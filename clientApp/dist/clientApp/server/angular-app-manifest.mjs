
export default {
  bootstrap: () => import('./main.server.mjs').then(m => m.default),
  inlineCriticalCss: true,
  baseHref: '/',
  locale: undefined,
  routes: [
  {
    "renderMode": 2,
    "route": "/"
  },
  {
    "renderMode": 2,
    "route": "/dashboard"
  },
  {
    "renderMode": 2,
    "route": "/control-panel"
  },
  {
    "renderMode": 2,
    "redirectTo": "/",
    "route": "/**"
  }
],
  entryPointToBrowserMapping: undefined,
  assets: {
    'index.csr.html': {size: 1067, hash: 'ab2452a8ab7fe2225b6439b36d0f901eb1cb422bb45d6fd7d2aa75f4f1d39985', text: () => import('./assets-chunks/index_csr_html.mjs').then(m => m.default)},
    'index.server.html': {size: 947, hash: '14319d0246e1c0211ccdec0cc6064aea1e8729a25c754712969590c80c6cc084', text: () => import('./assets-chunks/index_server_html.mjs').then(m => m.default)},
    'index.html': {size: 7881, hash: '6465df2d36db8c1cc5c1db73b97a939cdb1c8dddc5e163eee6b43ff23bff9137', text: () => import('./assets-chunks/index_html.mjs').then(m => m.default)},
    'control-panel/index.html': {size: 19606, hash: '2f74ac06f1dd5e8202d4d5efd0c8a735da8d7c1c115547d12d950666a044c03a', text: () => import('./assets-chunks/control-panel_index_html.mjs').then(m => m.default)},
    'dashboard/index.html': {size: 7706, hash: 'a3959ee1596d4ec081e033345b7adf33f65f69824fb0353b8bcb8373b511cff8', text: () => import('./assets-chunks/dashboard_index_html.mjs').then(m => m.default)},
    'styles-OBWGVD6K.css': {size: 514, hash: 'kZnghkHGYR0', text: () => import('./assets-chunks/styles-OBWGVD6K_css.mjs').then(m => m.default)}
  },
};
