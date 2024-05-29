from decimal import Decimal
from django.db import transaction
from rest_framework import serializers
from .signals import order_created
from .models import CartItem, Customer, Order, OrderItem, Product, Collection, Review, Cart


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'title', 'description', 'slug', 'inventory', 'unit_price', 'price_with_tax', 'collection']
    # id = serializers.IntegerField()
    # title = serializers.CharField(max_length=255)
    # unit_price = serializers.DecimalField(max_digits=8, decimal_places=2)
    price_with_tax = serializers.SerializerMethodField(method_name='calculate_tax')
    # collection = serializers.HyperlinkedRelatedField(
    #     queryset = Collection.objects.all(),
    #     view_name= 'collection-detail'
    # )

    def calculate_tax(self, product: Product):
        return product.unit_price * Decimal(1.18)
    

class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ['id', 'title', 'products_count']
    
    products_count = serializers.IntegerField(read_only=True)


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'date', 'name', 'description']
    
    def create(self, validated_data):
        product_id = self.context['product_id']
        return Review.objects.create(product_id=product_id, **validated_data)
    

class SimpleProductSerializer((serializers.ModelSerializer)):
    class Meta:
        model = Product
        fields = ['id', 'title', 'unit_price']


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'total_price']

    total_price = serializers.SerializerMethodField(method_name='get_total_price')
    product = SimpleProductSerializer()

    def get_total_price(self, item: CartItem):
        return item.product.unit_price * item.quantity


class CartSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField(method_name='get_total_price')

    def get_total_price(self, cart: Cart):
        return sum([item.quantity * item.product.unit_price for item in cart.items.all()])

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_price']


class AddCartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField()

    def validate_product_id(self, value):
        if not Product.objects.filter(pk=value).exists():
            raise serializers.ValidationError('No product with such a product id was found.')
        else:
            return value

    def save(self, **kwargs):
        cart_id = self.context['cart_id']
        product_id = self.validated_data['product_id']
        quantity = self.validated_data['quantity']

        try:
            cart_item = CartItem.objects.get(cart_id=cart_id, product_id=product_id)
            cart_item.quantity += quantity
            cart_item.save()
            self.instance = cart_item
        except CartItem.DoesNotExist:
            self.instance = CartItem.objects.create(cart_id=cart_id, **self.validated_data)
        
        return self.instance


    class Meta:
        model = CartItem
        fields = ['id', 'product_id', 'quantity']


class UpdateCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['quantity']


class CustomerSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True) 

    class Meta:
        model = Customer
        fields = ['id', 'user_id', 'phone', 'birth_date', 'membership']

    
class OrderItemSerializer(serializers.ModelSerializer):
    product = SimpleProductSerializer()
    unit_price = serializers.SerializerMethodField(method_name='get_unit_price', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'unit_price', 'quantity']

    
    def get_unit_price(self, orderitem: OrderItem):
        return orderitem.product.unit_price


class OrderSerializer(serializers.ModelSerializer):
    customer_id = serializers.IntegerField()
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'customer_id', 'placed_at', 'payment_status', 'items']


class CreateOrderSerializer(serializers.Serializer):
    cart_id = serializers.UUIDField()

    def validate_cart_id(self, cart_id):
        if not Cart.objects.filter(pk=cart_id).exists():
            raise serializers.ValidationError('No Cart with the given Id was found.')
        if CartItem.objects.filter(cart_id=cart_id).count() == 0:
            raise serializers.ValidationError('The cart is empty.')
        return cart_id

    @transaction.atomic()
    def save(self, **kwargs):
        cart_id = self.validated_data['cart_id']
        customer = Customer.objects.get(user_id=self.context['user_id'])
        order = Order.objects.create(customer=customer)

        cart_items = CartItem.objects.select_related('product').filter(cart_id=cart_id)
        order_items = [
            OrderItem(
                order=order,
                product=item.product,
                unit_price=item.product.unit_price,
                quantity=item.quantity
            ) for item in cart_items
        ]

        OrderItem.objects.bulk_create(order_items)
        Cart.objects.filter(pk=cart_id).delete()

        order_created.send_robust(self.__class__, order=order)

        return order


class UpdateOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['payment_status']
