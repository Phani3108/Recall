"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useDemo } from "./demo";
import { isStrictApiMode } from "./strict-api";

/**
 * Generic hook that tries to fetch from the real API, falling back to demo data.
 *
 * Usage:
 *   const { data, loading, isDemo } = useApiData(
 *     () => flow.listTasks(),   // real fetcher
 *     demoTasks,                // fallback
 *   );
 */
export function useApiData<T>(
  fetcher: () => Promise<T>,
  fallback: T,
): { data: T; loading: boolean; error: string | null; isDemo: boolean; refetch: () => void } {
  const { isDemo, markBackendDown, setApiReachabilityError } = useDemo();
  const [data, setData] = useState<T>(fallback);
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  const fetchData = useCallback(async () => {
    if (isDemo) {
      setData(fallback);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      if (mountedRef.current) {
        setApiReachabilityError(null);
        setData(result);
      }
    } catch (err: unknown) {
      if (mountedRef.current) {
        const isNetworkError =
          err instanceof TypeError ||
          (err instanceof Error && err.message.includes("fetch"));
        if (isNetworkError) {
          if (isStrictApiMode()) {
            setApiReachabilityError(
              "Cannot reach the Recall API. Check NEXT_PUBLIC_API_URL and that the backend is running.",
            );
            setData(fallback);
          } else {
            markBackendDown();
            setData(fallback);
          }
        } else {
          setError(err instanceof Error ? err.message : "Request failed");
          setData(fallback);
        }
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isDemo]);

  useEffect(() => {
    mountedRef.current = true;
    fetchData();
    return () => { mountedRef.current = false; };
  }, [fetchData]);

  return { data, loading, error, isDemo, refetch: fetchData };
}

/**
 * Same as useApiData but for multiple parallel fetches.
 */
export function useApiDataMulti<T extends unknown[]>(
  fetchers: { [K in keyof T]: () => Promise<T[K]> },
  fallbacks: T,
): { data: T; loading: boolean; error: string | null; isDemo: boolean; refetch: () => void } {
  const { isDemo, markBackendDown, setApiReachabilityError } = useDemo();
  const [data, setData] = useState<T>(fallbacks);
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  const fetchData = useCallback(async () => {
    if (isDemo) {
      setData(fallbacks);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const results = await Promise.all(fetchers.map((fn) => fn())) as T;
      if (mountedRef.current) {
        setApiReachabilityError(null);
        setData(results);
      }
    } catch (err: unknown) {
      if (mountedRef.current) {
        const isNetworkError =
          err instanceof TypeError ||
          (err instanceof Error && err.message.includes("fetch"));
        if (isNetworkError) {
          if (isStrictApiMode()) {
            setApiReachabilityError(
              "Cannot reach the Recall API. Check NEXT_PUBLIC_API_URL and that the backend is running.",
            );
            setData(fallbacks);
          } else {
            markBackendDown();
            setData(fallbacks);
          }
        } else {
          setError(err instanceof Error ? err.message : "Request failed");
          setData(fallbacks);
        }
      }
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isDemo]);

  useEffect(() => {
    mountedRef.current = true;
    fetchData();
    return () => { mountedRef.current = false; };
  }, [fetchData]);

  return { data, loading, error, isDemo, refetch: fetchData };
}
