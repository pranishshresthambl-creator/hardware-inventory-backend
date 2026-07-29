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

    class Meta:
        model = ComputerModel
        fields = '__all__'

class ComputerSerializer(serializers.ModelSerializer):
    model = ComputerModelSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)
    class Meta:
        model = Computer
        fields = '__all__'

class PrinterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Printer
        fields = '__all__'

class PrinterModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrinterModel
        fields = '__all__'