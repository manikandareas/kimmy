import fs from "node:fs";
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import hooks from "eslint-plugin-react-hooks";
import imports from "eslint-plugin-import";
import globals from "globals";
const features = fs.existsSync("src/features")
  ? fs
      .readdirSync("src/features", { withFileTypes: true })
      .filter((x) => x.isDirectory())
      .map((x) => x.name)
  : [];
export default tseslint.config(
  { ignores: ["dist", "src/types/api.generated.ts"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: { globals: globals.browser },
    plugins: { "react-hooks": hooks, import: imports },
    settings: { "import/resolver": { typescript: true } },
    rules: {
      ...hooks.configs.recommended.rules,
      "import/no-restricted-paths": [
        "error",
        {
          zones: [
            { target: "./src/features", from: "./src/app" },
            {
              target: ["./src/components", "./src/lib", "./src/types"],
              from: ["./src/app", "./src/features"],
            },
            ...features.map((name) => ({
              target: `./src/features/${name}`,
              from: "./src/features",
              except: [`./${name}`],
            })),
          ],
        },
      ],
    },
  },
  { files: ["*.js"], languageOptions: { globals: globals.node } },
);
