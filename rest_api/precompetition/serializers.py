import datetime
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers, exceptions
from multidb_account.precompetition.models import PreCompetition
from multidb_account.team.models import Team


class PreCompetitionCreateUpdateListSerializer(serializers.ModelSerializer):
    """
    Serializer for pre competition assessments.
    """

    team_id = serializers.IntegerField(required=False, allow_null=True)
    stress = serializers.IntegerField(max_value=4, min_value=1)
    fatigue = serializers.IntegerField(max_value=4, min_value=1)
    injury = serializers.IntegerField(max_value=4, min_value=1)
    weekly_load = serializers.IntegerField(max_value=4, min_value=1)
    hydration = serializers.IntegerField(max_value=4, min_value=1)

    athlete_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = PreCompetition
        fields = ('id', 'title', 'goal', 'athlete_id', 'team_id', 'date', 'stress', 'fatigue',
                  'injury', 'weekly_load', 'hydration')

    def create(self, validated_data):
        pre_competition = PreCompetition.objects.using(self.context.get('country')).create(**validated_data)
        pre_competition.save()
        return pre_competition

    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.goal = validated_data.get('goal', instance.goal)
        instance.team_id = validated_data.get('team_id', instance.team_id)
        instance.date = validated_data.get('date', instance.date)
        instance.stress = validated_data.get('stress', instance.stress)
        instance.fatigue = validated_data.get('fatigue', instance.fatigue)
        instance.injury = validated_data.get('injury', instance.injury)
        instance.weekly_load = validated_data.get('weekly_load', instance.weekly_load)
        instance.hydration = validated_data.get('hydration', instance.hydration)
        instance.save()
        return instance

    def validate(self, data):
        localized_db = self.context['country']
        data['athlete_id'] = self.context['uid']

        if data.get('date') < datetime.date.today():
            raise serializers.ValidationError({"date": _("Date must be set in the future.")})

        if 'team_id' in data:
            try:
                team = Team.objects.using(localized_db).get(id=data.get('team_id'))
                data['team_id'] = team.id
            except Team.DoesNotExist:
                raise serializers.ValidationError({"team_id": _("Unknown team")})

            if not team.has_team_member(self.context['user'].athleteuser):
                raise serializers.ValidationError({"team_id": _("User is not team member")})
        else:
            data['team_id'] = None

        return data