/**
 * EOS System — Custom Hooks
 */

import { useState, useEffect, useCallback } from 'react';
import { message } from 'antd';

export { useNetworkStatus } from './useNetworkStatus';

// =====================================================
// API Hook
// =====================================================

interface UseApiOptions {
  immediate?: boolean;
  onSuccess?: (data: any) => void;
  onError?: (error: any) => void;
}

interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: any;
  execute: (...args: any[]) => Promise<T | null>;
  reset: () => void;
}

export function useApi<T>(
  apiFunction: (...args: any[]) => Promise<T>,
  options: UseApiOptions = {}
): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<any>(null);

  const execute = useCallback(
    async (...args: any[]): Promise<T | null> => {
      setLoading(true);
      setError(null);

      try {
        const result = await apiFunction(...args);
        setData(result);
        options.onSuccess?.(result);
        return result;
      } catch (err) {
        setError(err);
        options.onError?.(err);
        message.error('حدث خطأ أثناء تنفيذ العملية');
        return null;
      } finally {
        setLoading(false);
      }
    },
    [apiFunction, options]
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return { data, loading, error, execute, reset };
}

// =====================================================
// Pagination Hook
// =====================================================

interface UsePaginationOptions {
  initialPage?: number;
  initialPageSize?: number;
  total: number;
}

interface UsePaginationResult {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  setPage: (page: number) => void;
  setPageSize: (pageSize: number) => void;
  reset: () => void;
}

export function usePagination(
  options: UsePaginationOptions
): UsePaginationResult {
  const [page, setPage] = useState(options.initialPage || 1);
  const [pageSize, setPageSize] = useState(options.initialPageSize || 20);

  const totalPages = Math.ceil(options.total / pageSize);

  const reset = useCallback(() => {
    setPage(1);
    setPageSize(20);
  }, []);

  return {
    page,
    pageSize,
    total: options.total,
    totalPages,
    setPage,
    setPageSize,
    reset,
  };
}

// =====================================================
// Search Hook
// =====================================================

interface UseSearchOptions {
  debounceMs?: number;
  onSearch?: (value: string) => void;
}

interface UseSearchResult {
  value: string;
  debouncedValue: string;
  setValue: (value: string) => void;
  clear: () => void;
}

export function useSearch(
  options: UseSearchOptions = {}
): UseSearchResult {
  const [value, setValue] = useState('');
  const [debouncedValue, setDebouncedValue] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
      options.onSearch?.(value);
    }, options.debounceMs || 300);

    return () => clearTimeout(timer);
  }, [value, options.debounceMs]);

  const clear = useCallback(() => {
    setValue('');
    setDebouncedValue('');
  }, []);

  return { value, debouncedValue, setValue, clear };
}

// =====================================================
// Confirmation Hook
// =====================================================

interface UseConfirmOptions {
  title: string;
  content: string;
  onConfirm: () => Promise<void> | void;
}

export function useConfirm(options: UseConfirmOptions) {
  const [loading, setLoading] = useState(false);

  const confirm = useCallback(async () => {
    setLoading(true);
    try {
      await options.onConfirm();
      message.success('تمت العملية بنجاح');
    } catch (error) {
      message.error('حدث خطأ أثناء تنفيذ العملية');
    } finally {
      setLoading(false);
    }
  }, [options]);

  return { confirm, loading };
}

// =====================================================
// Table Hook
// =====================================================

interface UseTableOptions<T> {
  fetchFunction: (params: any) => Promise<{ data: T[]; total: number }>;
  defaultPageSize?: number;
}

interface UseTableResult<T> {
  data: T[];
  loading: boolean;
  pagination: {
    current: number;
    pageSize: number;
    total: number;
    onChange: (page: number, pageSize: number) => void;
  };
  refresh: () => Promise<void>;
}

export function useTable<T>(
  options: UseTableOptions<T>
): UseTableResult<T> {
  const [data, setData] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: options.defaultPageSize || 20,
    total: 0,
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await options.fetchFunction({
        page: pagination.current,
        page_size: pagination.pageSize,
      });
      setData(result.data);
      setPagination((prev) => ({ ...prev, total: result.total }));
    } catch (error) {
      message.error('حدث خطأ أثناء تحميل البيانات');
    } finally {
      setLoading(false);
    }
  }, [pagination.current, pagination.pageSize]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handlePageChange = useCallback((page: number, pageSize: number) => {
    setPagination((prev) => ({ ...prev, current: page, pageSize }));
  }, []);

  return {
    data,
    loading,
    pagination: {
      current: pagination.current,
      pageSize: pagination.pageSize,
      total: pagination.total,
      onChange: handlePageChange,
    },
    refresh: fetchData,
  };
}

// =====================================================
// Form Hook
// =====================================================

interface UseFormOptions<T> {
  initialValues: T;
  validate?: (values: T) => Record<string, string>;
  onSubmit: (values: T) => Promise<void> | void;
}

export function useForm<T>(options: UseFormOptions<T>) {
  const [values, setValues] = useState<T>(options.initialValues);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const setValue = useCallback((field: keyof T, value: any) => {
    setValues((prev) => ({ ...prev, [field]: value }));
    // Clear error for this field
    setErrors((prev) => {
      const newErrors = { ...prev };
      delete newErrors[field as string];
      return newErrors;
    });
  }, []);

  const reset = useCallback(() => {
    setValues(options.initialValues);
    setErrors({});
  }, [options.initialValues]);

  const submit = useCallback(async () => {
    // Validate
    if (options.validate) {
      const validationErrors = options.validate(values);
      if (Object.keys(validationErrors).length > 0) {
        setErrors(validationErrors);
        return;
      }
    }

    setLoading(true);
    try {
      await options.onSubmit(values);
      message.success('تمت العملية بنجاح');
    } catch (error) {
      message.error('حدث خطأ أثناء تنفيذ العملية');
    } finally {
      setLoading(false);
    }
  }, [values, options]);

  return {
    values,
    errors,
    loading,
    setValue,
    reset,
    submit,
  };
}

// =====================================================
// Modal Hook
// =====================================================

interface UseModalResult {
  isOpen: boolean;
  open: () => void;
  close: () => void;
  toggle: () => void;
}

export function useModal(initialState: boolean = false): UseModalResult {
  const [isOpen, setIsOpen] = useState(initialState);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  return { isOpen, open, close, toggle };
}
