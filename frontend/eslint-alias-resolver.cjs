// Import resolver for ESLint (eslint-plugin-boundaries): "@/x" is "src/x", as
// in vite.config.js; everything else goes to the usual Node resolution.
const path = require('node:path');
const nodeResolver = require('eslint-import-resolver-node');

exports.interfaceVersion = 2;

exports.resolve = (source, file, config) => {
  const target = source.startsWith('@/') ? path.join(__dirname, 'src', source.slice(2)) : source;
  return nodeResolver.resolve(target, file, { extensions: ['.js', '.jsx'], ...config });
};
