from django.contrib.auth import get_user_model
from rest_framework import serializers, exceptions
from multidb_account.goal.models import Goal

UserModel = get_user_model()


class GoalSerializer(serializers.ModelSerializer):
    """
    Goal serializer.
    """

    user = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())

    class Meta:
        model = Goal
        read_only_fields = ('id', 'user', 'date_created')
        fields = read_only_fields + ('description', 'achieve_by', 'is_achieved')

    def create(self, validated_data):
        return self.Meta.model.objects.db_manager(validated_data['user'].country).create(**validated_data)

