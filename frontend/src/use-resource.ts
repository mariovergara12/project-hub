import { useCallback, useEffect, useState } from 'react';
import { api } from './api';
import { useAuth } from './auth-context';

export function refreshResources(paths: string[]) {
    window.dispatchEvent(new CustomEvent('resources-changed', { detail: paths }));
}

export function useResource<T>(path: string, load: (path: string, signal?: AbortSignal) => Promise<T> = api.get) {
    const { session } = useAuth();
    const [attempt, setAttempt] = useState(0);
    const reload = useCallback(() => setAttempt(value => value + 1), []);
    useEffect(() => {
        function changed(event: Event) {
            if ((event as CustomEvent<string[]>).detail.includes(path.split('?')[0])) reload();
        }
        window.addEventListener('resources-changed', changed);
        return () => window.removeEventListener('resources-changed', changed);
    }, [path, reload]);
    const key = `${session?.user.id}:${path}:${attempt}`;
    const [result, setResult] = useState<{ key: string; data?: T; error?: Error }>();
    useEffect(() => {
        const controller = new AbortController();
        load(path, controller.signal).then(
            data => { if (!controller.signal.aborted) setResult({ key, data }); },
            cause => {
                if (!controller.signal.aborted) setResult({ key, error: cause instanceof Error ? cause : new Error('Request failed') });
            },
        );
        return () => controller.abort();
    }, [path, key, load]);
    return {
        data: result?.key === key ? result.data : undefined,
        error: result?.key === key ? result.error : undefined,
        loading: result?.key !== key,
        reload,
    };
}
