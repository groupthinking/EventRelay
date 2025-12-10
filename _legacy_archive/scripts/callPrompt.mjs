import { runSavedPrompt } from "./openaiService.mjs";

const promptRef = {
  id: "pmpt_68eb823cde8481908178c5fd287c2955066a2c6374e32f71",
  version: "3",
};

async function main() {
  try {
    const { text, raw } = await runSavedPrompt(promptRef);

    if (text) {
      console.log(text);
    } else {
      console.dir(raw, { depth: null });
    }
  } catch (error) {
    console.error("Request failed:", error);
    process.exitCode = 1;
  }
}

main();
