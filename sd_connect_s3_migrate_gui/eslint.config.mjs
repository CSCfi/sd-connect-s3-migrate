import js from "@eslint/js";
import globals from "globals";
import pluginVue from "eslint-plugin-vue";
import eslintPluginPrettierRecommended from "eslint-plugin-prettier/recommended";
import { defineConfig } from "eslint/config";

export default defineConfig([
  {
    files: ["**/*.{js,mjs,cjs,vue}"],
    plugins: { js },
    extends: ["js/recommended"],
    languageOptions: {
      globals: {
        ...globals.node,
        MAIN_WINDOW_VITE_DEV_SERVER_URL: "readonly",
        MAIN_WINDOW_VITE_NAME: "readonly",
      },
    },
  },
  pluginVue.configs["flat/essential"],
  eslintPluginPrettierRecommended,
  {
    rules: {
      "prettier/prettier": [
        "error",
        {
          printWidth: 120,
          htmlWhitespaceSensitivity: "ignore",
        }
      ]
    }
  }
]);
