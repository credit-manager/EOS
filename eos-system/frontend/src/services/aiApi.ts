/**
 * EOS System — AI API Service
 */

import apiClient from './apiClient';
import type {
  ChatMessage,
  ChatRequest,
  ChatResponse,
  ForecastRequest,
  ForecastResponse,
  OCRRequest,
  OCRResponse,
} from '../types';

export const aiApi = {
  // =====================================================
  // Chat
  // =====================================================

  // Send chat message
  chat: async (data: ChatRequest): Promise<ChatResponse> => {
    return apiClient.post('/ai/chat', data);
  },

  // Get chat history
  getChatHistory: async (limit?: number): Promise<ChatMessage[]> => {
    return apiClient.get('/ai/chat/history', { params: { limit } });
  },

  // Clear chat history
  clearChatHistory: async (): Promise<void> => {
    return apiClient.delete('/ai/chat/history');
  },

  // =====================================================
  // Forecast
  // =====================================================

  // Get forecast
  getForecast: async (data: ForecastRequest): Promise<ForecastResponse> => {
    return apiClient.post('/ai/forecast', data);
  },

  // Get sales forecast
  getSalesForecast: async (periodDays?: number): Promise<ForecastResponse> => {
    return apiClient.post('/ai/forecast', {
      module: 'sales',
      metric: 'revenue',
      period_days: periodDays,
    });
  },

  // Get inventory forecast
  getInventoryForecast: async (
    productId: string,
    periodDays?: number
  ): Promise<ForecastResponse> => {
    return apiClient.post('/ai/forecast', {
      module: 'inventory',
      metric: 'stock_level',
      period_days: periodDays,
      filters: { product_id: productId },
    });
  },

  // Get cash flow forecast
  getCashFlowForecast: async (periodDays?: number): Promise<ForecastResponse> => {
    return apiClient.post('/ai/forecast', {
      module: 'cash_flow',
      metric: 'cash_balance',
      period_days: periodDays,
    });
  },

  // =====================================================
  // OCR
  // =====================================================

  // Process document with OCR
  processDocument: async (data: OCRRequest): Promise<OCRResponse> => {
    return apiClient.post('/ai/ocr', data);
  },

  // Process invoice
  processInvoice: async (imageUrl: string): Promise<OCRResponse> => {
    return apiClient.post('/ai/ocr', {
      image_url: imageUrl,
      document_type: 'invoice',
    });
  },

  // Process receipt
  processReceipt: async (imageUrl: string): Promise<OCRResponse> => {
    return apiClient.post('/ai/ocr', {
      image_url: imageUrl,
      document_type: 'receipt',
    });
  },

  // Process ID card
  processIdCard: async (imageUrl: string): Promise<OCRResponse> => {
    return apiClient.post('/ai/ocr', {
      image_url: imageUrl,
      document_type: 'id_card',
    });
  },

  // Process contract
  processContract: async (imageUrl: string): Promise<OCRResponse> => {
    return apiClient.post('/ai/ocr', {
      image_url: imageUrl,
      document_type: 'contract',
    });
  },

  // =====================================================
  // Anomaly Detection
  // =====================================================

  // Detect anomalies
  detectAnomalies: async (data: {
    module: string;
    metric: string;
    threshold?: number;
  }): Promise<any> => {
    return apiClient.post('/ai/anomaly', data);
  },

  // Detect sales anomalies
  detectSalesAnomalies: async (threshold?: number): Promise<any> => {
    return apiClient.post('/ai/anomaly', {
      module: 'sales',
      metric: 'revenue',
      threshold,
    });
  },

  // Detect expense anomalies
  detectExpenseAnomalies: async (threshold?: number): Promise<any> => {
    return apiClient.post('/ai/anomaly', {
      module: 'accounting',
      metric: 'expenses',
      threshold,
    });
  },

  // Detect inventory anomalies
  detectInventoryAnomalies: async (threshold?: number): Promise<any> => {
    return apiClient.post('/ai/anomaly', {
      module: 'inventory',
      metric: 'stock_movements',
      threshold,
    });
  },

  // =====================================================
  // Insights
  // =====================================================

  // Get business insights
  getInsights: async (data?: {
    module?: string;
    date_range?: { start: string; end: string };
  }): Promise<any> => {
    return apiClient.post('/ai/insights', data || {});
  },

  // Get sales insights
  getSalesInsights: async (): Promise<any> => {
    return apiClient.post('/ai/insights', { module: 'sales' });
  },

  // Get financial insights
  getFinancialInsights: async (): Promise<any> => {
    return apiClient.post('/ai/insights', { module: 'accounting' });
  },

  // Get inventory insights
  getInventoryInsights: async (): Promise<any> => {
    return apiClient.post('/ai/insights', { module: 'inventory' });
  },

  // =====================================================
  // Recommendations
  // =====================================================

  // Get product recommendations
  getProductRecommendations: async (productId: string): Promise<any> => {
    return apiClient.get(`/ai/recommendations/products/${productId}`);
  },

  // Get customer recommendations
  getCustomerRecommendations: async (customerId: string): Promise<any> => {
    return apiClient.get(`/ai/recommendations/customers/${customerId}`);
  },

  // Get pricing recommendations
  getPricingRecommendations: async (productId: string): Promise<any> => {
    return apiClient.get(`/ai/recommendations/pricing/${productId}`);
  },
};

export default aiApi;
