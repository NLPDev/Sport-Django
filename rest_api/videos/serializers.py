from rest_framework import serializers
from multidb_account.videos.models import Video
from rest_api.utils import get_youtube_video_id_from_url, get_vimeo_video_id_from_url, grab_video_name_from_url, \
    grab_video_url_from_embed_code
from multidb_account.constants import VIDEO_YOUTUBE, VIDEO_VIMEO


class VideoSerializer(serializers.ModelSerializer):
    """
    Video serializer.
    Takes video `url` as an input parameter to add/update.
    """

    url = serializers.CharField(write_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())

    class Meta:
        model = Video
        read_only_fields = ('id', 'user', 'video_type', 'video_id', 'video_name', 'date_added')
        fields = read_only_fields + ('url',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.video_id = self.video_type = self.video_name = None

    def validate_url(self, value):
        value = value.strip() if value else ''

        url = grab_video_url_from_embed_code(value)

        # Check if it's a youtube video
        self.video_id, self.video_type = get_youtube_video_id_from_url(url), VIDEO_YOUTUBE
        if self.video_id:
            self.video_name = grab_video_name_from_url(url)

        # Check if it's a vimeo video
        if self.video_id is None:
            self.video_id, self.video_type = get_vimeo_video_id_from_url(url), VIDEO_VIMEO
            if self.video_id:
                self.video_name = grab_video_name_from_url(url)

        return url

    def validate(self, attrs):
        if self.video_type is None or self.video_id is None:
            raise serializers.ValidationError("Provided video url is not recognized.")

        attrs.pop('url', None)
        attrs.update({
            'video_type': self.video_type,
            'video_id': self.video_id,
            'video_name': self.video_name,
        })

        return attrs

    def create(self, validated_data):
        return self.Meta.model.objects.db_manager(validated_data['user'].country).create(**validated_data)
