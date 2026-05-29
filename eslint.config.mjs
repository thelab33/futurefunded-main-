import js from "@eslint/js";
import globals from "globals";

export default [
  {
    ignores: [
      "node_modules/**",
      "playwright-report*/**",
      "test-results/**",
      "dist/**",
      "coverage/**",
      "artifacts/**",
      ".venv/**",
    ],
  },
  js.configs.recommended,
  {
    files: ["apps/web/app/static/js/**/*.js", "tests/**/*.js", "scripts/**/*.mjs"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      "no-console": "off",
      "no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
        },
      ],
      "no-constant-binary-expression": "error",
      "no-duplicate-imports": "error",
      "no-template-curly-in-string": "error",
      "object-shorthand": ["warn", "always"],
      "prefer-const": "warn",
    },
  },
  {
    files: ["scripts/**/*.mjs"],
    languageOptions: {
      sourceType: "module",
    },
  },
];
