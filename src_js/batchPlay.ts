/**
 * UXP batchPlay template.
 *
 * The Python side replaces the empty `data` array with action descriptors and
 * executes the generated script inside Photoshop.
 */
import { action, core } from "photoshop";
import { ActionDescriptor } from "photoshop/dom/CoreModules";

const data: ActionDescriptor[] = [];

/** Execute the injected action descriptors in one modal batchPlay call. */
async function doBatchPlay() {
  return await action.batchPlay(data, {});
}
core.executeAsModal(doBatchPlay, {
  commandName: "Programmatic Batch Play",
});
