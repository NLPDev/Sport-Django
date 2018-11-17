from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers, exceptions

from multidb_account.sport.models import Sport, ChosenSport

UserModel = get_user_model()


class SportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sport
        fields = ('id', 'name', 'description', 'is_available')
        extra_kwargs = {
            'id': {},
            'is_available': {},
        }

    def create(self, validated_data):
        sport = Sport.objects.using(self.context['country']).create(**validated_data)
        sport.save()
        return sport

    def validate(self, data):
        if Sport.objects.using(self.context['country']).filter(name=data.get('name')):
            raise serializers.ValidationError("This sport already exists")

        return data


class ChosenSportSerializer(serializers.Serializer):
    """
    Serializer for user's chosen sports.
    """
    sport_id = serializers.IntegerField(required=True)
    is_chosen = serializers.BooleanField(required=True)
    is_displayed = serializers.BooleanField(required=True)
    # Read-only
    sport = serializers.CharField(read_only=True)

    def create(self, validated_data):
        # create is called here because we don't pass an instance but a list of instances, that the only way for now
        # to update a list of instances at the same time
        # TODO: This should be refactored in the futur
        instance = ChosenSport.objects.using(self.localized_db).get(user=self.context['user'],
                                                                    sport_id=validated_data.get('sport_id'))
        instance.is_chosen = validated_data.get('is_chosen', instance.is_chosen)
        instance.is_displayed = validated_data.get('is_displayed', instance.is_displayed)
        instance.save()
        return instance

    def validate(self, data):
        self.localized_db = self.context['country']

        try:
            sport = Sport.objects.using(self.localized_db).filter(pk=data.get('sport_id'))
        except Sport.DoesNotExist:
            raise serializers.ValidationError({"sport_id": "Unknown sport."})

        try:
            ChosenSport.objects.using(self.localized_db).get(user=self.context['user'], sport=sport)
        except ChosenSport.DoesNotExist:
            raise serializers.ValidationError({"chosen_sports": "This sport is unknown or unavailable to this user."})
        return data


