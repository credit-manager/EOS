/**
 * EOS System — Inventory API Service
 */

import apiClient from './apiClient';
import type {
  Product,
  ProductCreate,
  Category,
  Warehouse,
  WarehouseCreate,
  StockMovement,
  StockMovementCreate,
  LowStockAlert,
  PaginatedResponse,
} from '../types';

export const inventoryApi = {
  // =====================================================
  // Products
  // =====================================================

  // List products
  listProducts: async (params?: {
    category_id?: string;
    search?: string;
    is_active?: boolean;
    low_stock?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Product>> => {
    return apiClient.get('/inventory/products', { params });
  },

  // Get product by ID
  getProduct: async (id: string): Promise<Product> => {
    return apiClient.get(`/inventory/products/${id}`);
  },

  // Create product
  createProduct: async (data: ProductCreate): Promise<Product> => {
    return apiClient.post('/inventory/products', data);
  },

  // Update product
  updateProduct: async (id: string, data: Partial<ProductCreate>): Promise<Product> => {
    return apiClient.put(`/inventory/products/${id}`, data);
  },

  // Delete product
  deleteProduct: async (id: string): Promise<void> => {
    return apiClient.delete(`/inventory/products/${id}`);
  },

  // =====================================================
  // Categories
  // =====================================================

  // List categories
  listCategories: async (): Promise<Category[]> => {
    return apiClient.get('/inventory/categories');
  },

  // Create category
  createCategory: async (data: Partial<Category>): Promise<Category> => {
    return apiClient.post('/inventory/categories', data);
  },

  // Update category
  updateCategory: async (id: string, data: Partial<Category>): Promise<Category> => {
    return apiClient.put(`/inventory/categories/${id}`, data);
  },

  // Delete category
  deleteCategory: async (id: string): Promise<void> => {
    return apiClient.delete(`/inventory/categories/${id}`);
  },

  // =====================================================
  // Warehouses
  // =====================================================

  // List warehouses
  listWarehouses: async (): Promise<Warehouse[]> => {
    return apiClient.get('/inventory/warehouses');
  },

  // Create warehouse
  createWarehouse: async (data: WarehouseCreate): Promise<Warehouse> => {
    return apiClient.post('/inventory/warehouses', data);
  },

  // Update warehouse
  updateWarehouse: async (id: string, data: Partial<WarehouseCreate>): Promise<Warehouse> => {
    return apiClient.put(`/inventory/warehouses/${id}`, data);
  },

  // Delete warehouse
  deleteWarehouse: async (id: string): Promise<void> => {
    return apiClient.delete(`/inventory/warehouses/${id}`);
  },

  // =====================================================
  // Stock Movements
  // =====================================================

  // List stock movements
  listStockMovements: async (params?: {
    product_id?: string;
    warehouse_id?: string;
    movement_type?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<StockMovement>> => {
    return apiClient.get('/inventory/stock/movements', { params });
  },

  // Create stock movement
  createStockMovement: async (data: StockMovementCreate): Promise<StockMovement> => {
    return apiClient.post('/inventory/stock/movements', data);
  },

  // Get stock by product
  getStockByProduct: async (productId: string): Promise<any> => {
    return apiClient.get(`/inventory/stock/product/${productId}`);
  },

  // =====================================================
  // Alerts
  // =====================================================

  // Get low stock alerts
  getLowStockAlerts: async (): Promise<LowStockAlert[]> => {
    return apiClient.get('/inventory/stock/alerts');
  },

  // =====================================================
  // Purchase Orders
  // =====================================================

  // List purchase orders
  listPurchaseOrders: async (params?: {
    status?: string;
    supplier_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<any>> => {
    return apiClient.get('/inventory/purchase-orders', { params });
  },

  // Create purchase order
  createPurchaseOrder: async (data: any): Promise<any> => {
    return apiClient.post('/inventory/purchase-orders', data);
  },

  // Receive purchase order
  receivePurchaseOrder: async (id: string): Promise<{ message: string }> => {
    return apiClient.post(`/inventory/purchase-orders/${id}/receive`);
  },

  // =====================================================
  // Suppliers
  // =====================================================

  // List suppliers
  listSuppliers: async (params?: {
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<any>> => {
    return apiClient.get('/inventory/suppliers', { params });
  },

  // Create supplier
  createSupplier: async (data: any): Promise<any> => {
    return apiClient.post('/inventory/suppliers', data);
  },

  // Update supplier
  updateSupplier: async (id: string, data: any): Promise<any> => {
    return apiClient.put(`/inventory/suppliers/${id}`, data);
  },

  // Delete supplier
  deleteSupplier: async (id: string): Promise<void> => {
    return apiClient.delete(`/inventory/suppliers/${id}`);
  },
};

export default inventoryApi;
