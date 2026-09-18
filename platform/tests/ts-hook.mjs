// Registreert de resolver hieronder. Zie ts-resolve.mjs voor het waarom.
import { register } from "node:module";

register(new URL("./ts-resolve.mjs", import.meta.url));
