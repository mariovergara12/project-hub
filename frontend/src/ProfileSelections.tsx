import { useRef, useState } from 'react';
import { api, loadCatalog } from './api';
import { useResource } from './use-resource';
import type { CatalogItem, Me, Page } from './types';

type Kind = 'skills' | 'interests';
type SelectionResponse = { skills: CatalogItem[] } | { interests: CatalogItem[] };

function SelectionGroup({ kind, initial, onSaved }: { kind: Kind; initial: CatalogItem[]; onSaved?: (kind: Kind, items: CatalogItem[]) => void }) {
    const catalog = useResource<Page<CatalogItem>>(`/${kind}`, loadCatalog);
    const [selected, setSelected] = useState(() => new Set(initial.map(item => item.id)));
    const [pending, setPending] = useState(false);
    const submitting = useRef(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');
    const title = kind === 'skills' ? 'Skills' : 'Interests';
    async function save() {
        if (submitting.current || !catalog.data) return;
        submitting.current = true;
        setPending(true);
        setError('');
        setMessage('');
        try {
            const field = kind === 'skills' ? 'skill_ids' : 'interest_ids';
            const result = await api.put<SelectionResponse>(`/me/${kind}`, {
                [field]: [...selected],
            });
            const saved = 'skills' in result ? result.skills : result.interests;
            setSelected(new Set(saved.map(item => item.id)));
            setMessage(`${title} saved.`);
            onSaved?.(kind, saved);
        } catch (cause) {
            setError(cause instanceof Error ? cause.message : `Could not save ${kind}.`);
        } finally { submitting.current = false; setPending(false); }
    }
    return <section aria-label={`Your ${kind}`}>
        <h2>{title}</h2>
        <p>Choose up to 50. Save an empty selection to clear your {kind}.</p>
        {catalog.loading && <p role="status">Loading {kind}…</p>}
        {catalog.error && <p role="alert">{catalog.error.message} <button onClick={catalog.reload}>Retry {kind}</button></p>}
        <fieldset disabled={pending || !catalog.data} className="selection-fields">
            <legend>Select {kind}</legend>
            {catalog.data?.items.length === 0 && <p>No {kind} available.</p>}
            {catalog.data?.items.map(item => <label key={item.id} className="selection-option">
                <input type="checkbox" checked={selected.has(item.id)}
                    disabled={!selected.has(item.id) && selected.size >= 50}
                    onChange={event => {
                        const next = new Set(selected);
                        if (event.target.checked) next.add(item.id); else next.delete(item.id);
                        setSelected(next);
                        setMessage('');
                    }} />
                {item.name}
            </label>)}
            <button type="button" onClick={save}>{pending ? `Saving ${kind}…` : `Save ${kind}`}</button>
        </fieldset>
        {message && <p role="status">{message}</p>}
        {error && <p role="alert">{error}</p>}
    </section>;
}

export function ProfileSelections({ me, onSaved }: { me: Me; onSaved?: (kind: Kind, items: CatalogItem[]) => void }) {
    return <>
        <SelectionGroup kind="skills" initial={me.skills || []} onSaved={onSaved} />
        <SelectionGroup kind="interests" initial={me.interests || []} onSaved={onSaved} />
    </>;
}
