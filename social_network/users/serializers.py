from rest_framework import serializers

from .models import User
from .hunter_service import email_hunter
from .clearbit_service import clearbit_enrichment


class UserDetailSerializer(serializers.ModelSerializer):

    user_url = serializers.HyperlinkedIdentityField(view_name='user-detail')
    posts_count = serializers.ReadOnlyField(source='posts.count')
    liked_posts_count = serializers.ReadOnlyField(source='liked_posts.count')

    class Meta:
        model = User
        exclude = ('password',)
        read_only_fields = ('email', 'is_superuser', 'is_staff', 'date_joined', 'last_login')


class UserCreationSerializer(UserDetailSerializer):
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)
    date_of_birth = serializers.DateField(required=False)
    avatar = serializers.URLField(required=False)
    bio = serializers.CharField(max_length=None, min_length=None, allow_blank=True, required=False)

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'password', 'confirm_password',
                  'date_of_birth', 'avatar', 'bio')

    def create(self, validated_data):
        password = validated_data.get('password', None)
        confirm_password = validated_data.pop('confirm_password', None)
        if password and confirm_password and password == confirm_password:
            instance = User.objects.create(**validated_data)
            instance.set_password(password)
            instance.save()

            return instance

    def validate(self, data):
        if data['password']:
            if data['password'] != data['confirm_password']:
                raise serializers.ValidationError(
                    "The passwords have to be the same"
                )
        return data


class UserCreationWithValidEmailSerializer(UserCreationSerializer):

    def validate(self, data):
        if data['password']:
            if data['password'] != data['confirm_password']:
                raise serializers.ValidationError(
                    "The passwords have to be the same"
                )
        if data['email']:
            result_data = email_hunter.email_verifier(data['email'])
            # gmail, hotmail and other popular mail systems will be considered as "risky"!
            if result_data['result'] not in ['deliverable', 'risky']:
                raise serializers.ValidationError(
                    "The email has to be real"
                )
        return data


class UserMiniSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'avatar')


class UserAdditionalDataSerializer(serializers.Serializer):

    email = serializers.EmailField(required=True)
    first_name = serializers.ReadOnlyField()
    last_name = serializers.ReadOnlyField()
    gender = serializers.ReadOnlyField()
    location = serializers.ReadOnlyField()
    bio = serializers.ReadOnlyField()
    site = serializers.ReadOnlyField()
    avatar = serializers.ReadOnlyField()

    class Meta:
        fields = '__all__'

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    def validate(self, data):
        if data['email']:
            additional_data = clearbit_enrichment(data['email'])
            if additional_data:
                data.update(additional_data)
            else:
                raise serializers.ValidationError(
                    "The email has to be real"
                )
        return data
