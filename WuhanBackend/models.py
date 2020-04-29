# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Newsinfo(models.Model):
    newsid = models.CharField(primary_key=True, max_length=64)
    title = models.CharField(max_length=255)
    time = models.DateTimeField()
    content = models.TextField()
    url = models.CharField(max_length=255)
    customer = models.CharField(max_length=255)
    emotion = models.IntegerField()
    entities = models.CharField(max_length=255)
    keyword = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    pageview = models.IntegerField()
    userview = models.IntegerField()
    words = models.CharField(max_length=255)
    theme_label = models.CharField(max_length=255)
    content_label = models.CharField(max_length=255)
    country_label = models.CharField(max_length=255)

    class Meta:
        # managed = False
        db_table = 'newsinfo'


class Viewsinfo(models.Model):
    viewid = models.AutoField(primary_key=True)
    personname = models.CharField(max_length=255)
    orgname = models.CharField(max_length=255)
    pos = models.CharField(max_length=255)
    verb = models.CharField(max_length=255)
    viewpoint = models.TextField()
    newsid = models.CharField(max_length=64)
    # newsid = models.ForeignKey('Newsinfo')
    sentiment = models.FloatField()
    time = models.DateTimeField()
    original_text = models.TextField()

    class Meta:
        # managed = False
        db_table = 'viewsinfo'
