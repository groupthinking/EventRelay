import { useState, useEffect, useRef, useCallback } from 'react';

// Debounce interfaces
export interface DebounceOptions {
  delay: number;
  leading?: boolean;
  trailing?: boolean;
  maxWait?: number;
}

export interface DebouncedFunction<T extends (...args: any[]) => any> {
  (...args: Parameters<T>): void;
  cancel: () => void;
  flush: () => void;
  isPending: () => boolean;
}

export const useDebounce = <T>(value: T, delay: number): T => {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

export const useDebouncedCallback = <T extends (...args: any[]) => any>(
  callback: T,
  options: DebounceOptions
): DebouncedFunction<T> => {
  const { delay, leading = false, trailing = true, maxWait } = options;
  
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastCallTimeRef = useRef<number>(0);
  const lastCallArgsRef = useRef<Parameters<T> | null>(null);
  const isPendingRef = useRef(false);

  const cancel = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    isPendingRef.current = false;
    lastCallArgsRef.current = null;
  }, []);

  const flush = useCallback(() => {
    if (lastCallArgsRef.current && isPendingRef.current) {
      callback(...lastCallArgsRef.current);
      cancel();
    }
  }, [callback, cancel]);

  const isPending = useCallback(() => {
    return isPendingRef.current;
  }, []);

  const debouncedCallback = useCallback((...args: Parameters<T>) => {
    const now = Date.now();
    lastCallArgsRef.current = args;
    isPendingRef.current = true;

    // Leading edge execution
    if (leading && !timeoutRef.current) {
      callback(...args);
      lastCallTimeRef.current = now;
    }

    // Clear existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Check if maxWait has been exceeded
    if (maxWait && now - lastCallTimeRef.current >= maxWait) {
      if (trailing) {
        callback(...args);
      }
      lastCallTimeRef.current = now;
      isPendingRef.current = false;
      return;
    }

    // Set new timeout
    timeoutRef.current = setTimeout(() => {
      if (trailing) {
        callback(...args);
      }
      lastCallTimeRef.current = Date.now();
      isPendingRef.current = false;
      timeoutRef.current = null;
    }, delay);
  }, [callback, delay, leading, trailing, maxWait]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cancel();
    };
  }, [cancel]);

  return Object.assign(debouncedCallback, {
    cancel,
    flush,
    isPending,
  });
};

export const useDebouncedState = <T>(
  initialValue: T,
  delay: number
): [T, T, (value: T) => void] => {
  const [value, setValue] = useState<T>(initialValue);
  const debouncedValue = useDebounce(value, delay);

  return [value, debouncedValue, setValue];
};

export const useDebouncedEffect = <T>(
  effect: () => void | (() => void),
  dependencies: T[],
  delay: number
) => {
  const debouncedDeps = useDebounce(dependencies, delay);

  useEffect(effect, debouncedDeps);
};

export const useDebouncedAsyncCallback = <T extends (...args: any[]) => Promise<any>>(
  callback: T,
  options: DebounceOptions & {
    onSuccess?: (result: Awaited<ReturnType<T>>) => void;
    onError?: (error: any) => void;
  }
): DebouncedFunction<T> => {
  const { onSuccess, onError, ...debounceOptions } = options;
  
  const wrappedCallback = useCallback(async (...args: Parameters<T>) => {
    try {
      const result = await callback(...args);
      onSuccess?.(result);
      return result;
    } catch (error) {
      onError?.(error);
      throw error;
    }
  }, [callback, onSuccess, onError]);

  return useDebouncedCallback(wrappedCallback, debounceOptions);
};

export const useDebouncedSearch = <T>(
  searchFunction: (query: string) => Promise<T[]>,
  options: DebounceOptions & {
    minQueryLength?: number;
    onResults?: (results: T[]) => void;
    onError?: (error: any) => void;
  } = { delay: 300 }
) => {
  const {
    minQueryLength = 2,
    onResults = () => {},
    onError = () => {},
    ...debounceOptions
  } = options;

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<T[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const debouncedSearch = useDebouncedAsyncCallback(
    async (searchQuery: string) => {
      if (searchQuery.length < minQueryLength) {
        setResults([]);
        return [];
      }

      setIsSearching(true);
      setError(null);

      try {
        const searchResults = await searchFunction(searchQuery);
        setResults(searchResults);
        onResults(searchResults);
        return searchResults;
      } catch (err: any) {
        const errorMessage = err.message || 'Search failed';
        setError(errorMessage);
        onError(err);
        setResults([]);
        throw err;
      } finally {
        setIsSearching(false);
      }
    },
    {
      ...debounceOptions,
      onError: (err: any) => {
        setError(err.message || 'Search failed');
        onError(err);
      },
    }
  );

  const search = useCallback((searchQuery: string) => {
    setQuery(searchQuery);
    debouncedSearch(searchQuery);
  }, [debouncedSearch]);

  const clearSearch = useCallback(() => {
    setQuery('');
    setResults([]);
    setError(null);
    debouncedSearch.cancel();
  }, [debouncedSearch]);

  return {
    query,
    results,
    isSearching,
    error,
    search,
    clearSearch,
    debouncedSearch,
  };
};

export const useDebouncedForm = <T extends Record<string, any>>(
  initialValues: T,
  options: DebounceOptions & {
    onSubmit?: (values: T) => void;
    onValidation?: (values: T) => string[] | null;
  } = { delay: 300 }
) => {
  const { onSubmit, onValidation, ...debounceOptions } = options;

  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({});
  const [isValidating, setIsValidating] = useState(false);

  const debouncedValidation = useDebouncedAsyncCallback(
    async (formValues: T) => {
      if (!onValidation) return null;

      setIsValidating(true);
      try {
        const validationErrors = onValidation(formValues);
        if (validationErrors) {
          const errorObject: Partial<Record<keyof T, string>> = {};
          validationErrors.forEach(error => {
            errorObject[error as keyof T] = error;
          });
          setErrors(errorObject);
        } else {
          setErrors({});
        }
        return validationErrors;
      } finally {
        setIsValidating(false);
      }
    },
    debounceOptions
  );

  const setValue = useCallback((key: keyof T, value: T[keyof T]) => {
    const newValues = { ...values, [key]: value };
    setValues(newValues);
    debouncedValidation(newValues);
  }, [values, debouncedValidation]);

  const setValuesBulk = useCallback((newValues: Partial<T>) => {
    const updatedValues = { ...values, ...newValues };
    setValues(updatedValues);
    debouncedValidation(updatedValues);
  }, [values, debouncedValidation]);

  const reset = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    debouncedValidation.cancel();
  }, [initialValues, debouncedValidation]);

  const submit = useCallback(() => {
    if (Object.keys(errors).length === 0) {
      onSubmit?.(values);
    }
  }, [values, errors, onSubmit]);

  return {
    values,
    errors,
    isValidating,
    setValue,
    setValuesBulk,
    reset,
    submit,
    debouncedValidation,
  };
};
