from django.db.models.query import QuerySet
from django.db import models, connection
from django.db.models.fields import FieldDoesNotExist

from django.conf import settings

from replay import Replay

def _not_exists(fieldname):
    raise FieldDoesNotExist('"%s" is not a ManyToManyField or a reverse ForeignKey relationship' % fieldname)

def _check_field_exists(model, fieldname):
    try:
        field_object, model, direct, m2m = model._meta.get_field_by_name(fieldname)
    except FieldDoesNotExist:
        # might be after reverse foreign key
        # which by default don't have the name we expect
        if fieldname.endswith('_set'):
            return _check_field_exists(model, fieldname[:-len('_set')])
        else:
            raise
    if not m2m:
        if direct: # reverse foreign key relationship
            _not_exists(fieldname)
    return fieldname

def _id_attr(id_column):
    # mangle the id column name, so we can make sure
    # the postgres doesn't complain about not quoting
    # field names (this helps make sure we don't clash
    # with the regular id column)
    return '__%s' % id_column.lower()

def _select_related_instances(related_model, related_name, ids, db_table, id_column):
    id__in_filter={ ('%s__pk__in' % related_name): ids }
    qn = connection.ops.quote_name
    select = { _id_attr(id_column): '%s.%s' % (qn(db_table), qn(id_column)) }
    related_instances = related_model._default_manager \
                            .filter(**id__in_filter) \
                            .extra(select=select)
    return related_instances

def batch_select(model, instances, target_field_name, fieldname, filter=None):
    '''
    basically do an extra-query to select the many-to-many
    field values into the instances given. e.g. so we can get all
    Entries and their Tags in two queries rather than n+1
    
    returns a list of the instances with the newly attached fields
    
    batch_select(Entry, Entry.objects.all(), 'tags_all', 'tags')
    
    would return a list of Entry objects with 'tags_all' fields
    containing the tags for that Entry
    
    filter is a function that can be used alter the extra-query - it 
    takes a queryset and returns a filtered version of the queryset
    
    NB: this is a semi-private API at the moment, but may be useful if you
    dont want to change your model/manager.
    '''
    
    fieldname = _check_field_exists(model, fieldname)
    
    instances = list(instances)
    ids = [instance.pk for instance in instances]
    
    field_object, model, direct, m2m = model._meta.get_field_by_name(fieldname)
    if m2m:
        if not direct:
            m2m_field = field_object.field
            related_model = field_object.model
            related_name = m2m_field.name
            id_column = m2m_field.m2m_reverse_name()
            db_table = m2m_field.m2m_db_table()
        else:
            m2m_field = field_object
            related_model = m2m_field.rel.to # model on other end of relationship
            related_name = m2m_field.related_query_name()
            id_column = m2m_field.m2m_column_name()
            db_table  = m2m_field.m2m_db_table()
    elif not direct:
        # handle reverse foreign key relationships
        fk_field = field_object.field
        related_model = field_object.model
        related_name  = fk_field.name
        id_column = fk_field.column
        db_table = related_model._meta.db_table
    
    related_instances = _select_related_instances(related_model, related_name, 
                                                  ids, db_table, id_column)
    
    if filter:
        related_instances = filter(related_instances)
    
    grouped = {}
    id_attr = _id_attr(id_column)
    for related_instance in related_instances:
        instance_id = getattr(related_instance, id_attr)
        group = grouped.get(instance_id, [])
        group.append(related_instance)
        grouped[instance_id] = group
    
    for instance in instances:
        setattr(instance, target_field_name, grouped.get(instance.pk, []))
    
    return instances

class Batch(Replay):
    # functions on QuerySet that we can invoke via this batch object
    __replayable__ = ('filter', 'exclude', 'annotate', 
                      'order_by', 'reverse', 'select_related',
                      'extra', 'defer', 'only')
    
    def __init__(self, m2m_fieldname, **filter):
        super(Batch,self).__init__()
        self.m2m_fieldname = m2m_fieldname
        self.target_field_name = '%s_all' % m2m_fieldname
        if filter: # add a filter replay method
            self._add_replay('filter', *(), **filter)
    
    def clone(self):
        cloned = super(Batch, self).clone(self.m2m_fieldname)
        cloned.target_field_name = self.target_field_name
        return cloned

class BatchQuerySet(QuerySet):
    
    def _clone(self, *args, **kwargs):
        query = super(BatchQuerySet, self)._clone(*args, **kwargs)
        batches = getattr(self, '_batches', None)
        if batches:
            query._batches = set(batches)
        return query
    
    def _create_batch(self, batch_or_str, target_field_name=None):
        batch = batch_or_str
        if isinstance(batch_or_str, basestring):
            batch = Batch(batch_or_str)
        if target_field_name:
            batch.target_field_name = target_field_name
        
        _check_field_exists(self.model, batch.m2m_fieldname)
        return batch
    
    def batch_select(self, *batches, **named_batches):
        batches = getattr(self, '_batches', set()) | \
                  set(self._create_batch(batch) for batch in batches) | \
                  set(self._create_batch(batch, target_field_name) \
                        for target_field_name, batch in named_batches.items())
        
        query = self._clone()
        query._batches = batches
        return query
    
    def iterator(self):
        result_iter = super(BatchQuerySet, self).iterator()
        batches = getattr(self, '_batches', None)
        if batches:
            results = list(result_iter)
            for batch in batches:
                results = batch_select(self.model, results,
                                       batch.target_field_name,
                                       batch.m2m_fieldname,
                                       batch.replay)
            return iter(results)
        return result_iter

class BatchManager(models.Manager):
    use_for_related_fields = True
    
    def get_query_set(self):
        return BatchQuerySet(self.model)
    
    def batch_select(self, *batches, **named_batches):
        return self.all().batch_select(*batches, **named_batches)

if getattr(settings, 'TESTING_BATCH_SELECT', False):
    class Tag(models.Model):
        name = models.CharField(max_length=32)
        
        objects = BatchManager()
    
    class Section(models.Model):
        name = models.CharField(max_length=32)
        
        objects = BatchManager()
    
    class Location(models.Model):
        name = models.CharField(max_length=32)
    
    class Entry(models.Model):
        title = models.CharField(max_length=255)
        section  = models.ForeignKey(Section, blank=True, null=True)
        location = models.ForeignKey(Location, blank=True, null=True)
        tags = models.ManyToManyField(Tag)
        
        objects = BatchManager()
    
    class Country(models.Model):
        # non id pk
        name = models.CharField(primary_key=True, max_length=100)
        locations = models.ManyToManyField(Location)
        
        objects = BatchManager()
        