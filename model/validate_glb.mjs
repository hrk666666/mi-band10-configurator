import fs from 'fs';
import validator from 'gltf-validator';

const path = process.argv[2] || 'public/models/mi_band10.glb';
const asset = fs.readFileSync(path);

validator.validateBytes(new Uint8Array(asset), { uri: path })
  .then((report) => {
    const issues = report.issues;
    console.log('GLB validation report:');
    console.log('  uri:', issues.uri);
    console.log('  errors:', issues.numErrors);
    console.log('  warnings:', issues.numWarnings);
    console.log('  infos:', issues.numInfos);
    if (issues.messages && issues.messages.length) {
      console.log('  messages:');
      issues.messages.forEach((m) => console.log('    -', m.severity, m.code, m.message));
    }
    if (issues.numErrors > 0) {
      process.exit(1);
    }
  })
  .catch((err) => {
    console.error('Validation failed:', err);
    process.exit(1);
  });
