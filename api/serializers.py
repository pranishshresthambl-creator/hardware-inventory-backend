from rest_framework import serializers
from django.utils import timezone
from inventory.models import Brand, Computer, ComputerModel, Department, Printer, PrinterModel, ComputerLog


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'

class ComputerModelSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(), source='brand', write_only=True, required=False
    )

    class Meta:
        model = ComputerModel
        fields = '__all__'

class ComputerSerializer(serializers.ModelSerializer):
    model = ComputerModelSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)
    model_id = serializers.PrimaryKeyRelatedField(
        queryset=ComputerModel.objects.all(), source='model', write_only=True, required=False, allow_null=True
    )
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source='department', write_only=True, required=False, allow_null=True
    )
    class Meta:
        model = Computer
        fields = '__all__'

class PrinterModelSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(), source='brand', write_only=True, required=False
    )

    class Meta:
        model = PrinterModel
        fields = '__all__'

class PrinterSerializer(serializers.ModelSerializer):
    model = PrinterModelSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)
    model_id = serializers.PrimaryKeyRelatedField(
        queryset=PrinterModel.objects.all(), source='model', write_only=True, required=False, allow_null=True
    )
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source='department', write_only=True, required=False, allow_null=True
    )
    class Meta:
        model = Printer
        fields = '__all__'


from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    role = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    last_login_formatted = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'is_staff',
            'is_superuser',
            'is_active',
            'last_login',
            'last_login_formatted',
            'role',
            'department_name',
            'status',
            'password',
        ]

    def get_role(self, obj):
        if obj.is_superuser:
            return 'Super Admin'
        if obj.is_staff:
            return 'Admin'
        return 'User'

    def get_department_name(self, obj):
        return 'IT'

    def get_status(self, obj):
        return 'ACTIVE' if obj.is_active else 'INACTIVE'

    def get_last_login_formatted(self, obj):
        if obj.last_login:
            local_dt = timezone.localtime(obj.last_login)
            return local_dt.strftime('%d %b %Y, %I:%M %p')
        if obj.date_joined:
            local_dt = timezone.localtime(obj.date_joined)
            return local_dt.strftime('%d %b %Y, %I:%M %p')
        return None

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        role = self.initial_data.get('role')
        if role == 'Super Admin':
            validated_data['is_superuser'] = True
            validated_data['is_staff'] = True
        elif role == 'Admin':
            validated_data['is_staff'] = True
            validated_data['is_superuser'] = False
        else:
            validated_data['is_staff'] = False
            validated_data['is_superuser'] = False

        status = self.initial_data.get('status')
        if status == 'INACTIVE':
            validated_data['is_active'] = False
        else:
            validated_data['is_active'] = True

        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_password('Admin@123')
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        role = self.initial_data.get('role')
        if role:
            if role == 'Super Admin':
                instance.is_superuser = True
                instance.is_staff = True
            elif role == 'Admin':
                instance.is_staff = True
                instance.is_superuser = False
            else:
                instance.is_staff = False
                instance.is_superuser = False

        status = self.initial_data.get('status')
        if status:
            instance.is_active = (status != 'INACTIVE')

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

class ComputerLogSerializer(serializers.ModelSerializer):
    computer = ComputerSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)
    computer_id = serializers.PrimaryKeyRelatedField(
        queryset=Computer.objects.all(), source='computer', write_only=True, required=False, allow_null=True
    )
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source='department', write_only=True, required=False, allow_null=True
    )
    log_date_formatted = serializers.SerializerMethodField()
    display_ims = serializers.SerializerMethodField()
    authorized_by_initials = serializers.SerializerMethodField()

    class Meta:
        model = ComputerLog
        fields = '__all__'

    def get_log_date_formatted(self, obj):
        if obj.log_date:
            local_dt = timezone.localtime(obj.log_date)
            return local_dt.strftime('%d %b %Y, %I:%M %p')
        return None

    def get_display_ims(self, obj):
        if obj.computer_ims:
            return obj.computer_ims
        if obj.computer and obj.computer.ims_code:
            return obj.computer.ims_code
        if obj.computer and obj.computer.host_name:
            return obj.computer.host_name
        return 'General Log'

    def get_authorized_by_initials(self, obj):
        name = obj.authorized_by or 'Admin'
        parts = name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        return name[:2].upper()