from rest_framework import serializers

from multidb_account.help_center.models import HelpCenterReport, OrganisationSupport


class HelpCenterReportSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())

    class Meta:
        model = HelpCenterReport
        read_only_fields = ('owner',)
        fields = read_only_fields + ('organization', 'coach_name', 'date', 'details', 'name')

    def create(self, validated_data):
        return self.Meta.model.objects.db_manager(validated_data['owner'].country).create(**validated_data)


class OrganisationSupportSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())

    class Meta:
        model = OrganisationSupport
        read_only_fields = ('owner',)
        fields = read_only_fields + ('email', 'phone_number', 'details', 'name', 'support_type')

    def create(self, validated_data):
        validated_data['organisation'] = validated_data['owner'].organisation
        return self.Meta.model.objects.db_manager(validated_data['owner'].country).create(**validated_data)
