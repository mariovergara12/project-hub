import { useLayoutEffect, useId, useRef } from 'react';

export function ConfirmDialog({ title, description, confirmLabel, pending, error, cancel, confirm }: {
    title: string; description: string; confirmLabel: string; pending: boolean;
    error?: string; cancel: () => void; confirm: () => void;
}) {
    const dialog = useRef<HTMLDialogElement>(null);
    const titleId = useId();
    const descriptionId = useId();
    useLayoutEffect(() => {
        const element = dialog.current;
        element?.showModal();
        return () => element?.close();
    }, []);
    return <dialog ref={dialog} className="confirmation-dialog" aria-labelledby={titleId} aria-describedby={descriptionId}
        onCancel={event => { event.preventDefault(); if (!pending) cancel(); }}
        onClick={event => { if (!pending && event.target === event.currentTarget) cancel(); }}>
        <h2 id={titleId}>{title}</h2><p id={descriptionId}>{description}</p>
        {error && <p role="alert">{error}</p>}
        <div className="confirmation-actions"><button autoFocus disabled={pending} onClick={cancel}>Cancel</button><button className="button-danger" disabled={pending} onClick={confirm}>{pending ? 'Saving…' : confirmLabel}</button></div>
    </dialog>;
}
