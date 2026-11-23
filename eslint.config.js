// Settings for ESLint, the JavaScript style checker. See "Coding standards" in CLAUDE.md.

import js from "@eslint/js";
import stylistic from "@stylistic/eslint-plugin";
import globals from "globals";

export default [
  { ignores: ["node_modules/"] },
  js.configs.recommended,
  {
    files: ["web/**/*.js", "web/**/*.mjs", "*.js"],
    plugins: { "@stylistic": stylistic },
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: { ...globals.browser, ...globals.worker, loadPyodide: "readonly" },
    },
    rules: {
      "no-var": "error",
      "prefer-const": "error",
      "no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "@stylistic/max-len": ["error", {
        code: 100, ignoreUrls: true,
      }],
      "@stylistic/quotes": ["error", "double", { avoidEscape: true }],
      "@stylistic/semi": ["error", "always"],
      "@stylistic/indent": ["error", 2, { SwitchCase: 1 }],
    },
  },
  {
    files: ["web/tests/**", "web/engine-core.js"],
    languageOptions: { globals: { ...globals.node } },
  },
];
