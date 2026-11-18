import { useEffect, useRef, useState } from 'react';

export function useMutation() {
    const [pending, setPending] = useState(false);
    const [error, setError] = useState('');
    const active = useRef<AbortController | null>(null);
    useEffect(() => () => active.current?.abort(), []);
    async function run(task: (signal: AbortSignal) => Promise<unknown>, onSuccess: () => void) {
        if (active.current) return;
        const controller = new AbortController();
        active.current = controller;
        setPending(true);
        setError('');
        try {
            await task(controller.signal);
            if (!controller.signal.aborted) onSuccess();
        } catch (cause) {
            if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Could not save the change.');
        } finally {
            active.current = null;
            if (!controller.signal.aborted) setPending(false);
        }
    }
    return { pending, error, run };
}
