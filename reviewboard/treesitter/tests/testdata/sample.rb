#!/usr/bin/env ruby
# frozen_string_literal: true

require 'json'
require 'net/http'
require 'uri'

# Module for utility functions
module Utils
  # Class method example
  def self.format_currency(amount, currency = 'USD')
    case currency.upcase
    when 'USD'
      "$#{'%.2f' % amount}"
    when 'EUR'
      "€#{'%.2f' % amount}"
    else
      "#{currency} #{'%.2f' % amount}"
    end
  end

  # Module method that gets included
  def titleize(str)
    str.split(/[\s_-]+/).map(&:capitalize).join(' ')
  end
end

# Base class demonstrating inheritance
class Product
  include Utils

  attr_reader :id, :name, :price, :created_at
  attr_accessor :description, :category

  # Class variables and constants
  @@next_id = 1
  CATEGORIES = %w[electronics clothing books home].freeze

  def initialize(name, price, description: nil, category: 'general')
    @id = @@next_id
    @@next_id += 1
    @name = name
    @price = price.to_f
    @description = description
    @category = category
    @created_at = Time.now
  end

  # Instance method with different visibility levels
  def formatted_price(currency = 'USD')
    Utils.format_currency(@price, currency)
  end

  def to_h
    {
      id: @id,
      name: @name,
      price: @price,
      description: @description,
      category: @category,
      created_at: @created_at.iso8601
    }
  end

  def to_json(*args)
    to_h.to_json(*args)
  end

  # Operator overloading
  def ==(other)
    other.is_a?(Product) && @id == other.id
  end

  def <=>(other)
    @price <=> other.price
  end

  protected

  def validate!
    raise ArgumentError, 'Name cannot be empty' if @name.nil? || @name.empty?
    raise ArgumentError, 'Price must be positive' if @price <= 0
    raise ArgumentError, 'Invalid category' unless CATEGORIES.include?(@category)
  end

  private

  def log_action(action)
    puts "[#{Time.now}] #{action} for product #{@id}"
  end
end

# Child class with method overriding
class DigitalProduct < Product
  attr_reader :download_url, :file_size

  def initialize(name, price, download_url, file_size: nil, **kwargs)
    super(name, price, **kwargs)
    @download_url = download_url
    @file_size = file_size
    validate!
  end

  # Override parent method
  def to_h
    super.merge(
      download_url: @download_url,
      file_size: @file_size,
      type: 'digital'
    )
  end

  # New method specific to digital products
  def download_link_valid?
    uri = URI.parse(@download_url)
    uri.is_a?(URI::HTTP) || uri.is_a?(URI::HTTPS)
  rescue URI::InvalidURIError
    false
  end
end

# Mixin module
module Discountable
  def apply_discount(percentage)
    raise ArgumentError, 'Discount must be between 0 and 100' unless (0..100).cover?(percentage)

    original_price = @price
    @price = @price * (1 - percentage / 100.0)

    yield(original_price, @price) if block_given?

    @price
  end

  def discount_amount(percentage)
    (@price * percentage / 100.0).round(2)
  end
end

# Class with mixins and metaprogramming
class ProductCatalog
  include Enumerable

  def initialize
    @products = []
    @callbacks = Hash.new { |h, k| h[k] = [] }
  end

  # Metaprogramming: define callback methods
  %w[before_add after_add before_remove after_remove].each do |callback_name|
    define_method("#{callback_name}") do |&block|
      @callbacks[callback_name.to_sym] << block if block_given?
    end
  end

  def add_product(product)
    execute_callbacks(:before_add, product)
    @products << product
    execute_callbacks(:after_add, product)
    product
  end

  def remove_product(product)
    execute_callbacks(:before_remove, product)
    removed = @products.delete(product)
    execute_callbacks(:after_remove, product) if removed
    removed
  end

  # Enumerable implementation
  def each(&block)
    return enum_for(:each) unless block_given?
    @products.each(&block)
  end

  # Method with block handling
  def find_products(&block)
    return enum_for(:find_products) unless block_given?
    @products.select(&block)
  end

  # Ruby's powerful string interpolation and regex
  def search(query)
    pattern = /#{Regexp.escape(query.to_s)}/i
    find_products do |product|
      product.name =~ pattern ||
      (product.description && product.description =~ pattern)
    end
  end

  # Hash-like access with method_missing
  def method_missing(method_name, *args, &block)
    if method_name.to_s.start_with?('find_by_')
      attribute = method_name.to_s.sub('find_by_', '')
      find_products { |product| product.respond_to?(attribute) && product.send(attribute) == args.first }
    else
      super
    end
  end

  def respond_to_missing?(method_name, include_private = false)
    method_name.to_s.start_with?('find_by_') || super
  end

  private

  def execute_callbacks(event, product)
    @callbacks[event].each { |callback| callback.call(product) }
  end
end

# Singleton pattern using class variables
class ProductManager
  @@instance = nil

  def self.instance
    @@instance ||= new
  end

  private_class_method :new

  def initialize
    @catalog = ProductCatalog.new
    setup_callbacks
  end

  # Proc and lambda examples
  def bulk_import(products_data)
    success_count = 0
    error_handler = proc { |error| puts "Import error: #{error.message}" }

    products_data.each do |data|
      begin
        product = case data[:type]
                  when 'digital'
                    DigitalProduct.new(data[:name], data[:price], data[:download_url], **data.except(:type, :name, :price, :download_url))
                  else
                    Product.new(data[:name], data[:price], **data.except(:name, :price))
                  end

        product.extend(Discountable) if data[:discountable]
        @catalog.add_product(product)
        success_count += 1
      rescue => error
        error_handler.call(error)
      end
    end

    success_count
  end

  # Method with keyword arguments and splat operators
  def generate_report(format: :json, include_details: true, **options)
    products = @catalog.to_a

    case format
    when :json
      JSON.pretty_generate(
        summary: {
          total_products: products.size,
          total_value: products.sum(&:price),
          categories: products.group_by(&:category).transform_values(&:size)
        },
        products: include_details ? products.map(&:to_h) : []
      )
    when :csv
      # CSV generation would go here
      "CSV format not implemented"
    else
      raise ArgumentError, "Unsupported format: #{format}"
    end
  end

  private

  def setup_callbacks
    @catalog.after_add do |product|
      puts "Added product: #{product.name}"
    end

    @catalog.before_remove do |product|
      puts "Removing product: #{product.name}"
    end
  end
end

# Usage example and demonstration
if __FILE__ == $0
  # Create product manager
  manager = ProductManager.instance

  # Sample data for bulk import
  products_data = [
    {
      name: 'Ruby Programming Book',
      price: 29.99,
      description: 'Learn Ruby programming',
      category: 'books',
      discountable: true
    },
    {
      name: 'Digital Music Album',
      price: 9.99,
      type: 'digital',
      download_url: 'https://example.com/album.zip',
      file_size: '50MB',
      category: 'electronics'
    },
    {
      name: 'Wireless Headphones',
      price: 199.99,
      description: 'High-quality wireless headphones',
      category: 'electronics'
    }
  ]

  # Import products
  imported = manager.bulk_import(products_data)
  puts "Successfully imported #{imported} products"

  # Generate and display report
  puts "\n--- CATALOG REPORT ---"
  puts manager.generate_report(format: :json, include_details: false)
end
