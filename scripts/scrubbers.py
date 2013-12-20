import json
import uuid

from django.db.models import F

from stacktach import models


class ScrubberBase(object):
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def raws(self):
        """ Returns an iterable of Raws to scrub
        """
        return [].__iter__()

    def filter(self, raw_data):
        """ Returns whether or not the provided RawData needs to be scrubbed.
            If the implementing function parses the json body to determine
            if it needs to be scrubbed, it should be returned as the second
            return value. This is done so that it will not need to be parsed
            a second time for scrubbing. Negative matches need not return
            parsed json bodies

        @raw_data: a RawData dictionary
        """
        return True, None

    def scrub(self, body):
        """ Returns the scrubbed json body of the RawData.

        @body: Dictionary version of the RawData's json.
        """
        return body


class ExistsCreatedAt(ScrubberBase):

    def raws(self):
        filters = {
            'raw__when__gte': self.start,
            'raw__when__lte': self.end,
            'audit_period_ending__lt': F('audit_period_beginning') + (60*60*24)
        }
        exists = models.InstanceExists.objects.filter(**filters)
        exists = exists.select_related('raw')
        for exist in exists.iterator():
            rawdata = exist.raw
            yield {'json': rawdata.json}

    def filter(self, raw_data):
        if '+00:00' in raw_data['json']:
            body = json.loads(raw_data['json'])[1]
            created_at = body.get('payload', {}).get('created_at')
            if created_at and '+00:00' in created_at:
                return True, body
            else:
                return False, None
        else:
            return False, None

    def scrub(self, body):
        created_at = body['payload']['created_at']
        scrubbed_created_at = created_at.replace('+00:00', '')
        body['payload']['created_at'] = scrubbed_created_at
        body['message_id'] = str(uuid.uuid4())
        return body

