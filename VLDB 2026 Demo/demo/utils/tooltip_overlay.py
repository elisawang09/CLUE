"""
tooltip_overlay.py
------------------
Two-part tooltip architecture:

  Part 1 — Bootstrap iframe (components.html, static string):
      Runs ONCE per browser session. Escapes to window.parent to plant
      the tooltip <div> and a MutationObserver on the real Streamlit page.
      Because the HTML string never changes, Streamlit never re-creates
      this iframe — the observer lives for the entire page lifetime.

  Part 2 — node_tooltip_wrapper():
      Embeds description text as data-flow-tooltip on node label HTML.
      The observer's attached listeners find it by walking up the DOM.

Public API
~~~~~~~~~~
    inject_tooltip_overlay() -> None
    node_tooltip_wrapper(inner_html, description) -> str
"""

from __future__ import annotations
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# Static bootstrap script — MUST NEVER CHANGE after first render.
# Any change causes Streamlit to destroy and recreate the iframe,
# which would re-run the bootstrap and duplicate listeners.
# ---------------------------------------------------------------------------
_BOOTSTRAP_HTML = """<!DOCTYPE html><html><body>
<script>
(function() {
    if (window.parent.__flowTooltipInit) return;
    window.parent.__flowTooltipInit = true;

    const parentDoc = window.parent.document;
    const TIP_ATTR  = 'data-flow-tooltip';

    const tip = parentDoc.createElement('div');
    tip.id = 'flow-tooltip-widget';
    tip.style.cssText = [
        'position:fixed',
        'display:none',
        'z-index:99999',
        'background:#1E293B',
        'color:#F1F5F9',
        'padding:7px 12px',
        'border-radius:7px',
        'font-size:13px',
        'max-width:260px',
        'line-height:1.5',
        'pointer-events:none',
        'box-shadow:0 4px 16px rgba(0,0,0,.25)',
        'white-space:normal',
        'word-break:break-word',
    ].join(';');
    parentDoc.body.appendChild(tip);

    function showTip(text, x, y) {
        tip.textContent = text;
        tip.style.display = 'block';
        moveTip(x, y);
    }
    function hideTip() { tip.style.display = 'none'; }

    function moveTip(x, y) {
        const PAD = 14;
        // Use the visual viewport dimensions — this is what's actually
        // visible on screen regardless of scroll containers.
        const vw = window.parent.visualViewport
            ? window.parent.visualViewport.width
            : window.parent.innerWidth;
        const vh = window.parent.visualViewport
            ? window.parent.visualViewport.height
            : window.parent.innerHeight;

        tip.style.left = '0px';
        tip.style.top  = '0px';
        tip.style.display = 'block';
        const tw = tip.offsetWidth  || 220;
        const th = tip.offsetHeight || 44;

        // Prefer below-right; flip if it would overflow the visible viewport
        let left = x + PAD;
        let top  = y + PAD;
        if (left + tw > vw - 10) left = x - tw - PAD;
        if (top  + th > vh - 10) top  = y - th - PAD;

        // Hard-clamp so tooltip never goes off any edge
        left = Math.max(8, Math.min(left, vw - tw - 8));
        top  = Math.max(8, Math.min(top,  vh - th - 8));

        tip.style.left = left + 'px';
        tip.style.top  = top  + 'px';
    }

    function findTip(el, root) {
        while (el && el !== root) {
            if (el.hasAttribute && el.hasAttribute(TIP_ATTR))
                return el.getAttribute(TIP_ATTR);
            el = el.parentElement;
        }
        return null;
    }

    const attached = new WeakMap();

    function isAttached(iframe) {
        try {
            return attached.get(iframe) ===
                   (iframe.contentDocument || iframe.contentWindow.document);
        } catch(e) { return false; }
    }

    function attachDoc(iframe) {
        if (isAttached(iframe)) return;
        let doc;
        try { doc = iframe.contentDocument || iframe.contentWindow.document; }
        catch(e) { return; }
        if (!doc || !doc.body) return;

        attached.set(iframe, doc);
        console.log('[tooltip] attached ->', iframe.getAttribute('title') || '?');

        function coords(cx, cy) {
            // getBoundingClientRect() returns position relative to the
            // VIEWPORT (not the page) — correct for position:fixed tooltip.
            const r = iframe.getBoundingClientRect();
            return [r.left + cx, r.top + cy];
        }

        doc.addEventListener('mouseover', function(e) {
            const t = findTip(e.target, doc.body);
            if (t) {
                const [x, y] = coords(e.clientX, e.clientY);
                showTip(t, x, y);
            }
        }, true);

        doc.addEventListener('mousemove', function(e) {
            if (tip.style.display === 'block') {
                const [x, y] = coords(e.clientX, e.clientY);
                moveTip(x, y);
            }
        }, true);

        doc.addEventListener('mouseleave', hideTip, true);

        doc.addEventListener('mouseout', function(e) {
            const from = findTip(e.target, doc.body);
            const to   = findTip(e.relatedTarget, doc.body);
            if (from && !to) hideTip();
        }, true);
    }

    function tryAttach(iframe) {
        if (isAttached(iframe)) return;
        try {
            const doc = iframe.contentDocument || iframe.contentWindow.document;
            if (doc && doc.readyState === 'complete' && doc.body) attachDoc(iframe);
            iframe.addEventListener('load', function() { attachDoc(iframe); });
        } catch(e) {}
    }

    function scan() { parentDoc.querySelectorAll('iframe').forEach(tryAttach); }

    scan();

    new MutationObserver(function(mutations) {
        mutations.forEach(function(m) {
            m.addedNodes.forEach(function(n) {
                if (n.tagName === 'IFRAME') tryAttach(n);
                else if (n.querySelectorAll) n.querySelectorAll('iframe').forEach(tryAttach);
            });
        });
    }).observe(parentDoc.body, { childList: true, subtree: true });

    setInterval(scan, 2000);
})();
</script>
</body></html>"""

def inject_tooltip_overlay() -> None:
    """
    Inject the persistent tooltip bootstrap.

    Call once at the top of render_main_view() and render_simulator_view().
    Streamlit caches the iframe because the HTML string never changes —
    the MutationObserver planted on window.parent survives all reruns.
    """
    components.html(_BOOTSTRAP_HTML, height=0, scrolling=False)
