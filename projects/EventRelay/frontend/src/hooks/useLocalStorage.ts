import { useState, useCallback, useEffect, useRef } from 'react';

// Local storage interfaces
export interface StorageItem<T> {
  value: T;
  timestamp: number;
  version?: string;
  checksum?: string;
}

export interface StorageOptions<T> {
  key: string;
  defaultValue: T;
  version?: string;
  validate?: (value: any) => value is T;
  serialize?: (value: T) => string;
  deserialize?: (value: string) => T;
  encrypt?: boolean;
  encryptionKey?: string;
  ttl?: number; // Time to live in milliseconds
  compression?: boolean;
  onError?: (error: Error) => void;
  onSync?: (value: T) => void;
}

export interface StorageState<T> {
  value: T;
  isLoading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  isStale: boolean;
  size: number; // Size in bytes
}

export const useLocalStorage = <T>(options: StorageOptions<T>) => {
  const {
    key,
    defaultValue,
    version = '1.0.0',
    validate,
    serialize = JSON.stringify,
    deserialize = JSON.parse,
    encrypt = false,
    encryptionKey = 'uvai_default_key',
    ttl,
    compression = false,
    onError = () => {},
    onSync = () => {},
  } = options;

  const [state, setState] = useState<StorageState<T>>({
    value: defaultValue,
    isLoading: true,
    error: null,
    lastUpdated: null,
    isStale: false,
    size: 0,
  });

  const storageKey = `uvai_${key}`;
  const isInitializedRef = useRef(false);
  const storageEventRef = useRef<((e: StorageEvent) => void) | null>(null);

  // Simple encryption/decryption (for basic use cases)
  const encryptValue = useCallback((value: string): string => {
    if (!encrypt) return value;
    
    try {
      // Simple XOR encryption (not for production use)
      const key = encryptionKey.split('').map(c => c.charCodeAt(0));
      const encrypted = value.split('').map((c, i) => 
        String.fromCharCode(c.charCodeAt(0) ^ key[i % key.length])
      ).join('');
      
      return btoa(encrypted);
    } catch (error) {
      console.warn('Encryption failed, storing as plain text:', error);
      return value;
    }
  }, [encrypt, encryptionKey]);

  const decryptValue = useCallback((value: string): string => {
    if (!encrypt) return value;
    
    try {
      const encrypted = atob(value);
      const key = encryptionKey.split('').map(c => c.charCodeAt(0));
      const decrypted = encrypted.split('').map((c, i) => 
        String.fromCharCode(c.charCodeAt(0) ^ key[i % key.length])
      ).join('');
      
      return decrypted;
    } catch (error) {
      console.warn('Decryption failed, returning encrypted value:', error);
      return value;
    }
  }, [encrypt, encryptionKey]);

  // Compress/decompress (simple gzip-like for text)
  const compressValue = useCallback((value: string): string => {
    if (!compression) return value;
    
    try {
      // Simple compression for repeated characters
      let compressed = '';
      let count = 1;
      let current = value[0];
      
      for (let i = 1; i < value.length; i++) {
        if (value[i] === current) {
          count++;
        } else {
          compressed += (count > 3 ? `${count}${current}` : current.repeat(count));
          current = value[i];
          count = 1;
        }
      }
      compressed += (count > 3 ? `${count}${current}` : current.repeat(count));
      
      return compressed.length < value.length ? `C:${compressed}` : value;
    } catch (error) {
      console.warn('Compression failed, storing uncompressed:', error);
      return value;
    }
  }, [compression]);

  const decompressValue = useCallback((value: string): string => {
    if (!compression || !value.startsWith('C:')) return value;
    
    try {
      const compressed = value.slice(2);
      let decompressed = '';
      let i = 0;
      
      while (i < compressed.length) {
        if (/\d/.test(compressed[i])) {
          let count = '';
          while (i < compressed.length && /\d/.test(compressed[i])) {
            count += compressed[i];
            i++;
          }
          if (compressed[i]) {
            decompressed += compressed[i].repeat(parseInt(count));
            i++;
          }
        } else {
          decompressed += compressed[i];
          i++;
        }
      }
      
      return decompressed;
    } catch (error) {
      console.warn('Decompression failed, returning compressed value:', error);
      return value;
    }
  }, [compression]);

  // Calculate checksum for validation
  const calculateChecksum = useCallback((value: string): string => {
    let hash = 0;
    for (let i = 0; i < value.length; i++) {
      const char = value.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return hash.toString(36);
  }, []);

  // Load value from storage
  const loadFromStorage = useCallback((): T => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (!stored) return defaultValue;

      // Decrypt if needed
      let decrypted = stored;
      if (encrypt) {
        decrypted = decryptValue(stored);
      }

      // Decompress if needed
      let decompressed = decrypted;
      if (compression) {
        decompressed = decompressValue(decrypted);
      }

      const parsed = deserialize(decompressed);
      
      // Validate parsed value
      if (validate && !validate(parsed)) {
        console.warn(`Invalid value for key ${key}, using default`);
        return defaultValue;
      }

      // Check version compatibility
      if (parsed.version && parsed.version !== version) {
        console.warn(`Version mismatch for key ${key}, using default`);
        return defaultValue;
      }

      // Check TTL if specified
      if (ttl && parsed.timestamp && Date.now() - parsed.timestamp > ttl) {
        console.warn(`Value for key ${key} has expired, using default`);
        localStorage.removeItem(storageKey);
        return defaultValue;
      }

      // Verify checksum if available
      if (parsed.checksum) {
        const calculatedChecksum = calculateChecksum(decompressed);
        if (parsed.checksum !== calculatedChecksum) {
          console.warn(`Checksum mismatch for key ${key}, using default`);
          return defaultValue;
        }
      }

      return parsed.value;
    } catch (error) {
      console.error(`Failed to load value for key ${key}:`, error);
      onError(error as Error);
      return defaultValue;
    }
  }, [
    storageKey, 
    defaultValue, 
    encrypt, 
    decryptValue, 
    compression, 
    decompressValue, 
    deserialize, 
    validate, 
    key, 
    version, 
    ttl, 
    calculateChecksum, 
    onError
  ]);

  // Save value to storage
  const saveToStorage = useCallback((value: T): boolean => {
    try {
      const storageItem: StorageItem<T> = {
        value,
        timestamp: Date.now(),
        version,
      };

      let serialized = serialize(storageItem);
      
      // Calculate checksum
      storageItem.checksum = calculateChecksum(serialized);
      serialized = serialize(storageItem);

      // Compress if needed
      let compressed = serialized;
      if (compression) {
        compressed = compressValue(serialized);
      }

      // Encrypt if needed
      let encrypted = compressed;
      if (encrypt) {
        encrypted = encryptValue(compressed);
      }

      localStorage.setItem(storageKey, encrypted);
      
      // Update state
      setState(prev => ({
        ...prev,
        value,
        lastUpdated: new Date(),
        isStale: false,
        size: encrypted.length,
      }));

      // Call sync callback
      onSync(value);
      
      return true;
    } catch (error) {
      console.error(`Failed to save value for key ${key}:`, error);
      onError(error as Error);
      setState(prev => ({ ...prev, error: (error as Error).message }));
      return false;
    }
  }, [
    storageKey, 
    version, 
    serialize, 
    calculateChecksum, 
    compression, 
    compressValue, 
    encrypt, 
    encryptValue, 
    key, 
    onSync, 
    onError
  ]);

  // Set value
  const setValue = useCallback((value: T | ((prev: T) => T)) => {
    const newValue = typeof value === 'function' ? (value as (prev: T) => T)(state.value) : value;
    saveToStorage(newValue);
  }, [state.value, saveToStorage]);

  // Remove value from storage
  const removeValue = useCallback(() => {
    try {
      localStorage.removeItem(storageKey);
      setState(prev => ({
        ...prev,
        value: defaultValue,
        lastUpdated: null,
        isStale: false,
        size: 0,
      }));
      onSync(defaultValue);
    } catch (error) {
      console.error(`Failed to remove value for key ${key}:`, error);
      onError(error as Error);
    }
  }, [storageKey, defaultValue, key, onSync, onError]);

  // Clear all storage
  const clearAll = useCallback(() => {
    try {
      // Remove all keys with our prefix
      const keysToRemove: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('uvai_')) {
          keysToRemove.push(key);
        }
      }
      
      keysToRemove.forEach(key => localStorage.removeItem(key));
      
      setState(prev => ({
        ...prev,
        value: defaultValue,
        lastUpdated: null,
        isStale: false,
        size: 0,
      }));
      
      onSync(defaultValue);
    } catch (error) {
      console.error('Failed to clear storage:', error);
      onError(error as Error);
    }
  }, [defaultValue, onSync, onError]);

  // Get storage info
  const getStorageInfo = useCallback(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (!stored) return null;

      const size = stored.length;
      const item = deserialize(stored);
      
      return {
        size,
        timestamp: item.timestamp ? new Date(item.timestamp) : null,
        version: item.version,
        isExpired: ttl && item.timestamp ? Date.now() - item.timestamp > ttl : false,
        age: item.timestamp ? Date.now() - item.timestamp : null,
      };
    } catch (error) {
      console.error(`Failed to get storage info for key ${key}:`, error);
      return null;
    }
  }, [storageKey, deserialize, ttl, key]);

  // Export storage data
  const exportData = useCallback(() => {
    try {
      const data = {
        key: storageKey,
        value: state.value,
        timestamp: state.lastUpdated?.toISOString(),
        version,
        size: state.size,
      };
      
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${key}_${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error(`Failed to export data for key ${key}:`, error);
      onError(error as Error);
    }
  }, [storageKey, state.value, state.lastUpdated, state.size, version, key, onError]);

  // Import storage data
  const importData = useCallback(async (file: File): Promise<boolean> => {
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      
      if (data.key === storageKey && data.version === version) {
        setValue(data.value);
        return true;
      } else {
        throw new Error('Invalid data format or version mismatch');
      }
    } catch (error) {
      console.error(`Failed to import data for key ${key}:`, error);
      onError(error as Error);
      return false;
    }
  }, [storageKey, version, setValue, key, onError]);

  // Listen for storage changes from other tabs/windows
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === storageKey && e.newValue !== e.oldValue) {
        try {
          const newValue = loadFromStorage();
          setState(prev => ({
            ...prev,
            value: newValue,
            lastUpdated: new Date(),
            isStale: false,
          }));
          onSync(newValue);
        } catch (error) {
          console.error(`Failed to sync storage change for key ${key}:`, error);
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);
    storageEventRef.current = handleStorageChange;

    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [storageKey, loadFromStorage, key, onSync]);

  // Initialize on mount
  useEffect(() => {
    if (!isInitializedRef.current) {
      try {
        const value = loadFromStorage();
        const info = getStorageInfo();
        
        setState({
          value,
          isLoading: false,
          error: null,
          lastUpdated: info?.timestamp || null,
          isStale: info?.isExpired || false,
          size: info?.size || 0,
        });
        
        isInitializedRef.current = true;
      } catch (error) {
        setState(prev => ({
          ...prev,
          isLoading: false,
          error: (error as Error).message,
        }));
      }
    }
  }, [loadFromStorage, getStorageInfo]);

  // Check for stale data periodically
  useEffect(() => {
    if (ttl) {
      const interval = setInterval(() => {
        const info = getStorageInfo();
        if (info?.isExpired) {
          setState(prev => ({ ...prev, isStale: true }));
        }
      }, Math.min(ttl / 10, 60000)); // Check every minute or 1/10th of TTL, whichever is smaller
      
      return () => clearInterval(interval);
    }
  }, [ttl, getStorageInfo]);

  return {
    // State
    ...state,
    
    // Actions
    setValue,
    removeValue,
    clearAll,
    
    // Utilities
    getStorageInfo,
    exportData,
    importData,
    
    // Raw access
    getRawValue: () => localStorage.getItem(storageKey),
    setRawValue: (value: string) => localStorage.setItem(storageKey, value),
  };
};
