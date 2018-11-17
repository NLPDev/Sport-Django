from rest_framework import serializers

from sport_engine.models import SportEngineEvent, SportEngineGame


class SportEngineEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SportEngineEvent
        fields = '__all__'


class SportEngineGameSerializer(serializers.ModelSerializer):
    class Meta:
        model = SportEngineGame
        fields = '__all__'
