import { useCallback, useEffect, useRef, useState, type DependencyList } from "react";

import { ApiError, toApiError } from "../services/api";

export interface ApiData<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  reload: () => Promise<void>;
  setData: (updater: T | null | ((current: T | null) => T | null)) => void;
}

/**
 * Load data from an API call, tracking loading/error state. Results from
 * outdated requests (after deps change or unmount) are ignored.
 */
export function useApiData<T>(load: () => Promise<T>, deps: DependencyList): ApiData<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const requestId = useRef(0);

  // `load` is re-created on every render; `deps` decides when to refetch.
  const run = useCallback(load, deps);

  const reload = useCallback(async () => {
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const result = await run();
      if (id === requestId.current) setData(result);
    } catch (err) {
      if (id === requestId.current) setError(toApiError(err));
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [run]);

  useEffect(() => {
    void reload();
    return () => {
      requestId.current += 1; // invalidate in-flight requests
    };
  }, [reload]);

  return { data, error, loading, reload, setData };
}
