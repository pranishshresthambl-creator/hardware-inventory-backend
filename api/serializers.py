from rest_framework import serializers
from inventory.models import Brand, Computer, ComputerModel, Department, Printer, PrinterModel


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