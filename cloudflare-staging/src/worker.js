const indexHtml = new TextDecoder().decode(Uint8Array.from(atob("PCFET0NUWVBFIGh0bWw+PGh0bWwgbGFuZz0iZGUiPjxoZWFkPjxtZXRhIGNoYXJzZXQ9IlVURi04Ij48bWV0YSBuYW1lPSJ2aWV3cG9ydCIgY29udGVudD0id2lkdGg9ZGV2aWNlLXdpZHRoLCBpbml0aWFsLXNjYWxlPTEiPjxtZXRhIG5hbWU9Imdvb2dsZS1zaXRlLXZlcmlmaWNhdGlvbiIgY29udGVudD0idGFkYmZ1MDlwU0sxcElqcS0zTXVTeDl6QVY5U2p6Sk11RnI3dE1FVFRZTSIgLz48dGl0bGU+SGV5LCBTdHV0ZW5zZWUhIOKAkyBWZXJhbnN0YWx0dW5nZW4gdW5kIFRlcm1pbmU8L3RpdGxlPjwhLS1TU1JfT0dfVEFHUy0tPjwhLS1TU1JfSlNPTl9MRC0tPjxtZXRhIG5hbWU9ImRlc2NyaXB0aW9uIiBjb250ZW50PSJBbGxlIFZlcmFuc3RhbHR1bmdlbiBpbiBTdHV0ZW5zZWUgYXVmIGVpbmVuIEJsaWNrOiBGZXN0ZSwgTcOkcmt0ZSwgU3BvcnQsIEtpcmNoZSwgS2luZGVyYW5nZWJvdGUgdW5kIG1laHIuIEdlZmlsdGVydCBuYWNoIE9ydHN0ZWlsIHVuZCBLYXRlZ29yaWUuIj48bGluayByZWw9Imljb24iIHR5cGU9ImltYWdlL3BuZyIgaHJlZj0iL2Zhdmljb24ucG5nIj48c3R5bGU+U1RZTEVfQ1NTX1BMQUNFSE9MREVSPC9zdHlsZT48L2hlYWQ+PGJvZHk+PGRpdiBjbGFzcz0icGFnZS1sZWZ0Ij48aGVhZGVyPjxkaXYgY2xhc3M9ImhlYWRlci1pbm5lciI+PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA1NTAgMTAwIiBjbGFzcz0ic2NoZHVkZXNlZS1sb2dvIiBzdHlsZT0iaGVpZ2h0OjY4cHg7d2lkdGg6YXV0bzsiPjxkZWZzPjxjbGlwUGF0aCBpZD0icy1jbGlwIj48dGV4dCB4PSI1NCIgeT0iNzgiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJzeXN0ZW0tdWksLWFwcGxlLXN5c3RlbSxzYW5zLXNlcmlmIiBmb250LXdlaWdodD0iODAwIiBmb250LXNpemU9IjgwIj5TPC90ZXh0PjwvY2xpcFBhdGg+PGNsaXBQYXRoIGlkPSJ0aXAtY2xpcCI+PHJlY3QgeD0iNTIiIHk9IjgiIHdpZHRoPSIyNCIgaGVpZ2h0PSIzMiIvPjwvY2xpcFBhdGg+PC9kZWZzPjx0ZXh0IHg9IjU0IiB5PSI3OCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9InN5c3RlbS11aSwtYXBwbGUtc3lzdGVtLHNhbnMtc2VyaWYiIGZvbnQtd2VpZ2h0PSI4MDAiIGZvbnQtc2l6ZT0iODAiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2ZmZmZmZiIgc3Ryb2tlLXdpZHRoPSI0IiBzdHJva2UtbGluZWpvaW49InJvdW5kIj5TPC90ZXh0Pjx0ZXh0IHg9IjU0IiB5PSI3OCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9InN5c3RlbS11aSwtYXBwbGUtc3lzdGVtLHNhbnMtc2VyaWYiIGZvbnQtd2VpZ2h0PSI4MDAiIGZvbnQtc2l6ZT0iODAiIGZpbGw9IiNmYWI4MDAiPlM8L3RleHQ+PHRleHQgeD0iNTQiIHk9Ijc4IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0ic3lzdGVtLXVpLC1hcHBsZS1zeXN0ZW0sc2Fucy1zZXJpZiIgZm9udC13ZWlnaHQ9IjgwMCIgZm9udC1zaXplPSI4MCIgZmlsbD0iI2RkMjkxYSIgY2xpcC1wYXRoPSJ1cmwoI3RpcC1jbGlwKSI+UzwvdGV4dD48ZyBjbGlwLXBhdGg9InVybCgjcy1jbGlwKSI+PHBhdGggY2xhc3M9IndhdmUtaW5uZXIiIGQ9Ik0tNSA2MCBRNSA1NCAxNSA2MCBRMjUgNjYgMzUgNjAgUTQ1IDU0IDU1IDYwIFE2NSA2NiA3NSA2MCBRODUgNTQgOTUgNjAiIHN0cm9rZT0iIzBkM2E3MSIgc3Ryb2tlLXdpZHRoPSIxMCIgZmlsbD0ibm9uZSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBvcGFjaXR5PSIxIi8+PHBhdGggY2xhc3M9IndhdmUtaW5uZXIiIGQ9Ik0tNSA2OSBRNSA2MyAxNSA2OSBRMjUgNzUgMzUgNjkgUTQ1IDYzIDU1IDY5IFE2NSA3NSA3NSA2OSBRODUgNjMgOTUgNjkiIHN0cm9rZT0iIzFhNTI5OSIgc3Ryb2tlLXdpZHRoPSIxMCIgZmlsbD0ibm9uZSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBvcGFjaXR5PSIxIiBzdHlsZT0iYW5pbWF0aW9uLWRlbGF5Oi0xcyIvPjxwYXRoIGNsYXNzPSJ3YXZlLWlubmVyIiBkPSJNLTUgNzggUTUgNzIgMTUgNzggUTI1IDg0IDM1IDc4IFE0NSA3MiA1NSA3OCBRNjUgODQgNzUgNzggUTg1IDcyIDk1IDc4IiBzdHJva2U9IiMzYTdiYzgiIHN0cm9rZS13aWR0aD0iMTAiIGZpbGw9Im5vbmUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgb3BhY2l0eT0iMSIgc3R5bGU9ImFuaW1hdGlvbi1kZWxheTotMnMiLz48L2c+PHRleHQgeD0iMTQwIiB5PSI2MCIgZm9udC1mYW1pbHk9InN5c3RlbS11aSwtYXBwbGUtc3lzdGVtLHNhbnMtc2VyaWYiIGZvbnQtd2VpZ2h0PSI3MDAiIGZvbnQtc2l6ZT0iMjYiIGZpbGw9IiNmZmZmZmYiPkhleSwgU3R1dGVuc2VlITwvdGV4dD48L3N2Zz48L2Rpdj48L2hlYWRlcj48ZGl2IGNsYXNzPSJjb250cm9scy13cmFwIj48ZGl2IGNsYXNzPSJjb250cm9scyI+PGRpdiBjbGFzcz0iY29udHJvbHMtcm93Ij48aW5wdXQgdHlwZT0idGV4dCIgaWQ9InNlYXJjaCIgcGxhY2Vob2xkZXI9IlN1Y2hlbuKApiIgYXJpYS1sYWJlbD0iU3VjaGUiIG9uaW5wdXQ9ImRlYm91bmNlU2VhcmNoKCkiPjxpbnB1dCB0eXBlPSJkYXRlIiBpZD0iZGF0ZS1mcm9tIiBvbmNoYW5nZT0ibG9hZEV2ZW50cygxKSIgdGl0bGU9IlZvbiI+PC9kaXY+PGRpdiBjbGFzcz0iY29udHJvbHMtcm93Ij48ZGl2IGNsYXNzPSJmaWx0ZXItcG9wb3ZlciIgaWQ9InRoZW1lLXBvcG92ZXIiPjxidXR0b24gY2xhc3M9ImZpbHRlci1idG4iIG9uY2xpY2s9InRvZ2dsZUZpbHRlclBvcG92ZXIoJ3RoZW1lJykiIGlkPSJ0aGVtZS1idG4iIGFyaWEtZXhwYW5kZWQ9ImZhbHNlIj5LYXRlZ29yaWUg4pa+PC9idXR0b24+PGRpdiBjbGFzcz0icG9wb3Zlci1kcm9wZG93biIgaWQ9InRoZW1lLWRyb3Bkb3duIj48L2Rpdj48L2Rpdj48ZGl2IGNsYXNzPSJmaWx0ZXItcG9wb3ZlciIgaWQ9ImxvY2F0aW9uLXBvcG92ZXIiPjxidXR0b24gY2xhc3M9ImZpbHRlci1idG4iIG9uY2xpY2s9InRvZ2dsZUZpbHRlclBvcG92ZXIoJ2xvY2F0aW9uJykiIGlkPSJsb2NhdGlvbi1idG4iIGFyaWEtZXhwYW5kZWQ9ImZhbHNlIj5PcnRzdGVpbCDilr48L2J1dHRvbj48ZGl2IGNsYXNzPSJwb3BvdmVyLWRyb3Bkb3duIiBpZD0ibG9jYXRpb24tZHJvcGRvd24iPjwvZGl2PjwvZGl2PjxkaXYgY2xhc3M9ImZpbHRlci1wb3BvdmVyIiBpZD0ib3JnYW5pemVyLXBvcG92ZXIiPjxidXR0b24gY2xhc3M9ImZpbHRlci1idG4iIG9uY2xpY2s9InRvZ2dsZUZpbHRlclBvcG92ZXIoJ29yZ2FuaXplcicpIiBpZD0ib3JnYW5pemVyLWJ0biIgYXJpYS1leHBhbmRlZD0iZmFsc2UiPlZlcmFuc3RhbHRlciDilr48L2J1dHRvbj48ZGl2IGNsYXNzPSJwb3BvdmVyLWRyb3Bkb3duIiBpZD0ib3JnYW5pemVyLWRyb3Bkb3duIj48aW5wdXQgdHlwZT0idGV4dCIgY2xhc3M9InBvcG92ZXItc2VhcmNoIiBpZD0ib3JnYW5pemVyLXNlYXJjaCIgcGxhY2Vob2xkZXI9IlN1Y2hlbuKApiIgb25pbnB1dD0iZmlsdGVyT3JnYW5pemVycygpIiBvbmNsaWNrPSJldmVudC5zdG9wUHJvcGFnYXRpb24oKSI+PGRpdiBjbGFzcz0icG9wb3Zlci1jaGlwcyIgaWQ9Im9yZ2FuaXplci1jaGlwcyI+PC9kaXY+PC9kaXY+PC9kaXY+PHNwYW4gY2xhc3M9InRvZ2dsZXMtZGVza3RvcCI+PGxhYmVsIGNsYXNzPSJyZWN1cnJpbmctdG9nZ2xlLXdyYXAiPjxzcGFuIGNsYXNzPSJ0b2dnbGUtc3dpdGNoIj48aW5wdXQgdHlwZT0iY2hlY2tib3giIGlkPSJjb25kZW5zZWQtdG9nZ2xlIiBvbmNoYW5nZT0idG9nZ2xlQ29uZGVuc2VkKCkiPjxzcGFuIGNsYXNzPSJ0b2dnbGUtc2xpZGVyIj48L3NwYW4+PC9zcGFuPjxzcGFuPktvbXBha3RhbnNpY2h0PC9zcGFuPjwvbGFiZWw+PGxhYmVsIGNsYXNzPSJyZWN1cnJpbmctdG9nZ2xlLXdyYXAiPjxzcGFuIGNsYXNzPSJ0b2dnbGUtc3dpdGNoIj48aW5wdXQgdHlwZT0iY2hlY2tib3giIGlkPSJzaG93LXJlY3VycmluZyIgY2hlY2tlZCBvbmNoYW5nZT0idG9nZ2xlUmVjdXJyaW5nRmlsdGVyKCkiPjxzcGFuIGNsYXNzPSJ0b2dnbGUtc2xpZGVyIj48L3NwYW4+PC9zcGFuPjxzcGFuPlplaWdlIHdpZWRlcmhvbGVuZGUgVGVybWluZTwvc3Bhbj48L2xhYmVsPjwvc3Bhbj48c3BhbiBzdHlsZT0icG9zaXRpb246cmVsYXRpdmU7ZGlzcGxheTppbmxpbmUtYmxvY2siPjxidXR0b24gY2xhc3M9InNldHRpbmdzLWJ0biIgb25jbGljaz0idG9nZ2xlU2V0dGluZ3NEcm9wZG93bigpIiB0aXRsZT0iRWluc3RlbGx1bmdlbiI+4pqZ77iPPC9idXR0b24+PGJ1dHRvbiBjbGFzcz0iY2hhdC1idG4iIG9uY2xpY2s9InRvZ2dsZUNoYXQoKSIgdGl0bGU9IktJLUNoYXQiPvCfpJY8L2J1dHRvbj48ZGl2IGNsYXNzPSJzZXR0aW5ncy1kcm9wZG93biIgaWQ9InNldHRpbmdzLWRyb3Bkb3duIj48bGFiZWwgY2xhc3M9InJlY3VycmluZy10b2dnbGUtd3JhcCI+PHNwYW4gY2xhc3M9InRvZ2dsZS1zd2l0Y2giPjxpbnB1dCB0eXBlPSJjaGVja2JveCIgaWQ9ImNvbmRlbnNlZC10b2dnbGUtbW9iaWxlIiBvbmNoYW5nZT0iZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2NvbmRlbnNlZC10b2dnbGUnKS5jaGVja2VkPXRoaXMuY2hlY2tlZDt0b2dnbGVDb25kZW5zZWQoKSI+PHNwYW4gY2xhc3M9InRvZ2dsZS1zbGlkZXIiPjwvc3Bhbj48L3NwYW4+PHNwYW4+S29tcGFrdGFuc2ljaHQ8L3NwYW4+PC9sYWJlbD48bGFiZWwgY2xhc3M9InJlY3VycmluZy10b2dnbGUtd3JhcCI+PHNwYW4gY2xhc3M9InRvZ2dsZS1zd2l0Y2giPjxpbnB1dCB0eXBlPSJjaGVja2JveCIgaWQ9InNob3ctcmVjdXJyaW5nLW1vYmlsZSIgY2hlY2tlZCBvbmNoYW5nZT0iZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3Nob3ctcmVjdXJyaW5nJykuY2hlY2tlZD10aGlzLmNoZWNrZWQ7dG9nZ2xlUmVjdXJyaW5nRmlsdGVyKCkiPjxzcGFuIGNsYXNzPSJ0b2dnbGUtc2xpZGVyIj48L3NwYW4+PC9zcGFuPjxzcGFuPlplaWdlIHdpZWRlcmhvbGVuZGUgVGVybWluZTwvc3Bhbj48L2xhYmVsPjwvZGl2Pjwvc3Bhbj48c3BhbiBjbGFzcz0iYWN0aXZlLXRhZ3MiIGlkPSJhY3RpdmUtdGFncyI+PC9zcGFuPjwvZGl2PjwvZGl2PjwvZGl2PjxkaXYgY2xhc3M9ImFwcC1sYXlvdXQiPjxtYWluIGNsYXNzPSJtYWluLWNvbnRlbnQiPjxkaXYgY2xhc3M9ImV2ZW50cy13cmFwIj48IS0tU1NSX0lOVFJPLS0+PGRpdiBpZD0iZXZlbnRzIiBjbGFzcz0iZXZlbnRzIj48IS0tU1NSX0VWRU5UUy0tPjwvZGl2PjxkaXYgY2xhc3M9InBhZ2luYXRpb24iIGlkPSJwYWdpbmF0aW9uIj48IS0tU1NSX1BBR0lOQVRJT04tLT48L2Rpdj48L2Rpdj48L21haW4+PC9kaXY+PGZvb3RlciBzdHlsZT0idGV4dC1hbGlnbjpjZW50ZXI7cGFkZGluZzoxNnB4O2ZvbnQtc2l6ZToxMnB4O2NvbG9yOnZhcigtLWZvb3Rlci10ZXh0KSI+PGEgaHJlZj0iIyIgb25jbGljaz0iZXZlbnQucHJldmVudERlZmF1bHQoKTtkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnaW1wcmludCcpLnN0eWxlLmRpc3BsYXk9J2Jsb2NrJyIgc3R5bGU9ImNvbG9yOnZhcigtLWZvb3Rlci10ZXh0KTt0ZXh0LWRlY29yYXRpb246dW5kZXJsaW5lIj5JbXByZXNzdW08L2E+PHNwYW4gc3R5bGU9Im1hcmdpbjowIDhweCI+wrc8L3NwYW4+PHNwYW4gaWQ9ImRhcmstdG9nZ2xlIiBvbmNsaWNrPSJ0b2dnbGVEYXJrKCkiIHN0eWxlPSJjdXJzb3I6cG9pbnRlcjtmb250LXNpemU6MTZweCIgdGl0bGU9IkRhcmsgTW9kZSB1bXNjaGFsdGVuIj7wn4yZPC9zcGFuPjxkaXYgaWQ9ImltcHJpbnQiIHN0eWxlPSJkaXNwbGF5Om5vbmU7bWFyZ2luLXRvcDoxMnB4O2NvbG9yOnZhcigtLWltcHJpbnQtdGV4dCk7bGluZS1oZWlnaHQ6MS42Ij48c3Ryb25nPkFuZ2FiZW4gZ2Vtw6TDnyDCpzUgVE1HPC9zdHJvbmc+PGJyPiBKb2hhbm5lcyBSZXV0ZXI8YnI+IEUtTWFpbDogZW1haWxAam9oYW5uZXMtcmV1dGVyLmRlPGJyPjxicj48c3Ryb25nPkhhZnR1bmcgZsO8ciBJbmhhbHRlPC9zdHJvbmc+PGJyPiBBbHMgRGllbnN0ZWFuYmlldGVyIHNpbmQgd2lyIGbDvHIgZWlnZW5lIEluaGFsdGUgYXVmIGRpZXNlciBTZWl0ZSB2ZXJhbnR3b3J0bGljaC48YnI+PHN0cm9uZz5EYXRlbnNjaHV0ejwvc3Ryb25nPjxicj4gRGllc2UgU2VpdGUgZXJoZWJ0IGtlaW5lcmxlaSBwZXJzb25lbmJlem9nZW5lIERhdGVuLiBFcyB3ZXJkZW4ga2VpbmUgQ29va2llcyBnZXNldHp0LCBrZWluIFRyYWNraW5nIGR1cmNoZ2Vmw7xocnQgdW5kIGtlaW5lIEFuYWx5c2VkaWVuc3RlIGdlbnV0enQuIDwvZGl2PjwvZm9vdGVyPjwvZGl2PjwhLS0gZW5kIHBhZ2UtbGVmdCAtLT48ZGl2IGlkPSJjaGF0LW1vdW50Ij48L2Rpdj48c2NyaXB0IHNyYz0iL2FwcC5qcyIgZGVmZXI+PC9zY3JpcHQ+PCEtLVNTUl9JTklUSUFMX0RBVEEtLT48c2NyaXB0IHNyYz0iL2NoYXQuanMiIGRlZmVyPjwvc2NyaXB0PjwvYm9keT48L2h0bWw+Cg=="), c=>c.charCodeAt(0)));
const faviconB64 = null;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/') {
      return new Response(indexHtml, { headers: { 'content-type': 'text/html;charset=utf-8' } });
    }
    if (url.pathname === '/favicon.png' && typeof faviconB64 !== 'undefined' && faviconB64) {
      const img = Uint8Array.from(atob(faviconB64), c => c.charCodeAt(0));
      return new Response(img, { headers: { 'content-type': 'image/png', 'cache-control': 'public, max-age=86400' } });
    }
    if (url.pathname === '/api/list') return serveEvents(env, url);
    if (url.pathname === '/api/theme') return serveTags(env);
    if (url.pathname === '/api/districts') return serveDistricts(env);
    if (url.pathname === '/api/organizer') return serveOrganizers(env);
    if (url.pathname === '/api/info') return serveStats(env);
    if (url.pathname.startsWith('/api/same/')) return serveRecurring(env, url.pathname.split('/').pop());
    if (url.pathname === '/robots.txt') return new Response('User-agent: *\nAllow: /\n', { headers: { 'content-type': 'text/plain;charset=utf-8' } });
    if (url.pathname === '/.well-known/security.txt') return serveSecurityTxt();
    if (url.pathname === '/sitemap.xml') return serveSitemapXml();
    return new Response('Not found', { status: 404 });
  }
};

function decode(s) {
  if (!s) return '';
  return s.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(n));
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'content-type': 'application/json;charset=utf-8', 'access-control-allow-origin': '*' }
  });
}

async function serveEvents(env, url) {
  const p = url.searchParams;
  const page = Math.max(1, parseInt(p.get('page') || '1'));
  const perPage = Math.min(100, Math.max(1, parseInt(p.get('per_page') || '50')));
  const search = p.get('search') || '';
  const tags = p.getAll('tag').filter(Boolean);
  const dateFrom = p.get('date_from') || '';
  const organizer = p.get('organizer') || '';

  const db = env.STUTENSEE_DB;
  const wheres = ["tags != 'blocked'"];
  const args = [];

  if (dateFrom) { wheres.push("date_start >= ?"); args.push(dateFrom); }
  if (search) { wheres.push("(title LIKE ? OR location LIKE ? OR organizer LIKE ?)"); args.push(`%${search}%`, `%${search}%`, `%${search}%`); }
  for (const t of tags) { wheres.push("tags LIKE ?"); args.push(`%${t}%`); }
  if (organizer) { wheres.push("organizer = ?"); args.push(organizer); }
  if (p.get('hide_recurring')) { wheres.push("recurring_group_id IS NULL"); }

  const where = wheres.length ? 'WHERE ' + wheres.join(' AND ') : '';
  const offset = (page - 1) * perPage;

  const total = (await db.prepare(`SELECT COUNT(*) as c FROM curated_events ${where}`).bind(...args).first()).c;
  const { results } = await db.prepare(
    `SELECT id, title, date_start, date_end, time_raw, location, organizer, description, event_url, sources, tags, recurring_group_id
     FROM curated_events ${where} ORDER BY date_start ASC, id LIMIT ? OFFSET ?`
  ).bind(...args, perPage, offset).all();

  return json({
    events: results.map(r => ({
      id: r.id, title: decode(r.title), date_start: r.date_start || '', date_end: r.date_end,
      time_raw: r.time_raw, location: decode(r.location), organizer: decode(r.organizer),
      description: decode(r.description), event_url: decode(r.event_url || ''),
      sources: decode(r.sources || ''), tags: r.tags || '',
      recurring_group_id: r.recurring_group_id,
    })),
    total, page, per_page: perPage,
    total_pages: Math.ceil(total / perPage),
  });
}

async function serveOrganizers(env) {
  const { results } = await env.STUTENSEE_DB.prepare(
    "SELECT DISTINCT organizer FROM curated_events WHERE organizer IS NOT NULL AND organizer != '' AND tags != 'blocked' ORDER BY organizer"
  ).all();
  return json(results.map(r => decode(r.organizer)));
}

async function serveTags(env) {
  const themeKeys = new Set(['Sport','Musik','Kultur','Kirche','Kinder','Fest','Markt','Workshop','Bildung','Natur','Senioren','Digital','Handwerk','Essen','Treff','Politik','Verein','Wohltätigkeit','Sonstiges']);
  const { results } = await env.STUTENSEE_DB.prepare(
    "SELECT DISTINCT tags FROM curated_events WHERE tags IS NOT NULL AND tags != '' AND tags != 'blocked'"
  ).all();
  const set = new Set();
  for (const r of results) {
    for (const t of r.tags.split(',')) { const s = t.trim(); if (s && themeKeys.has(s)) set.add(s); }
  }
  return json([...set].sort());
}

async function serveDistricts(env) {
  const themeKeys = new Set(['Sport','Musik','Kultur','Kirche','Kinder','Fest','Markt','Workshop','Bildung','Natur','Senioren','Digital','Handwerk','Essen','Treff','Politik','Verein','Wohltätigkeit','Sonstiges']);
  const { results } = await env.STUTENSEE_DB.prepare(
    "SELECT DISTINCT tags FROM curated_events WHERE tags IS NOT NULL AND tags != '' AND tags != 'blocked'"
  ).all();
  const set = new Set();
  for (const r of results) {
    for (const t of r.tags.split(',')) { const s = t.trim(); if (s && !themeKeys.has(s)) set.add(s); }
  }
  return json([...set].sort());
}

async function serveStats(env) {
  const [raw, curated] = await Promise.all([
    env.STUTENSEE_DB.prepare('SELECT COUNT(*) as c FROM raw_events').first(),
    env.STUTENSEE_DB.prepare('SELECT COUNT(*) as c FROM curated_events').first(),
  ]);
  return json({ raw: raw.c, curated: curated.c });
}

async function serveRecurring(env, groupId) {
  const { results } = await env.STUTENSEE_DB.prepare(
    `SELECT id, title, date_start, date_end, time_raw, location, organizer, substr(description,1,300) as description,
            event_url, sources, tags, recurring_group_id
     FROM curated_events WHERE recurring_group_id = ? ORDER BY date_start`
  ).bind(groupId).all();
  return json(results.map(r => ({
    id: r.id, title: decode(r.title), date_start: r.date_start || '', date_end: r.date_end,
    time_raw: r.time_raw, location: decode(r.location), organizer: decode(r.organizer),
    description: decode(r.description), event_url: decode(r.event_url || ''),
    sources: decode(r.sources || ''), tags: r.tags || '',
    recurring_group_id: r.recurring_group_id,
  })));
}

function serveSecurityTxt() {
  return new Response(`# Security Contact
# If you find a security issue on was-geht-stutensee.de, please report it.
Contact: mailto:email@johannes-reuter.de
Canonical: https://was-geht-stutensee.de/.well-known/security.txt
Preferred-Languages: de, en
Expires: 2027-05-24T14:00:00.000Z
`, {
    headers: { 'content-type': 'text/plain;charset=utf-8', 'cache-control': 'public, max-age=86400' }
  });
}

function serveSitemapXml() {
  return new Response(`<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://was-geht-stutensee.de/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>`, {
    headers: { 'content-type': 'application/xml;charset=utf-8', 'cache-control': 'public, max-age=86400' }
  });
}
