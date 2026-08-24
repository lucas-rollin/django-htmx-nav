/**
 * @fileoverview Navigates to the same page under a different variant. 
 */

function switchVariant(targetPrefix) {
  const activePrefix = document.body.dataset.variantPrefix; // e.g. "mpa/"
  const path = window.location.pathname; // e.g. "/mpa/orgs/1234/"

  let rest = "";
  if (activePrefix && path.startsWith("/" + activePrefix)) {
    rest = path.slice(("/" + activePrefix).length);
  }

  window.location.href = "/" + targetPrefix + rest + window.location.search;
}