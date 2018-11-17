from rest_framework.viewsets import ModelViewSet
from .permissions import IsOwnerOrReadOnly
from .serializers import VideoSerializer
from multidb_account.videos.models import Video


class VideoViewSet(ModelViewSet):
    """
    A viewset for viewing and editing user videos.
    """
    permission_classes = (IsOwnerOrReadOnly,)
    serializer_class = VideoSerializer

    def get_queryset(self):
        return Video.objects.using(self.request.user.country).filter(user=self.kwargs['uid'])

    def get_serializer(self, *args, **kwargs):
        if kwargs.get('data') is not None:
            kwargs['many'] = isinstance(kwargs.get('data'), list)
        return super().get_serializer(*args, **kwargs)
