const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('uvaiDemo', {
  platform: process.platform,
  version: '1.1.0',
  isElectron: true
});
