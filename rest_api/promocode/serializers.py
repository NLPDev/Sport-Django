from rest_framework import serializers

from multidb_account.promocode.models import Promocode


class PromocodeSerializer(serializers.ModelSerializer):
    """
    Promocode serializer.
    """

    class Meta:
        model = Promocode
        fields = ('code', 'discount')
