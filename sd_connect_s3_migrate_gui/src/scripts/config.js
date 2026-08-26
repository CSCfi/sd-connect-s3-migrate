// Config variables for the application

export async function getOpenstackAuthEndpoint() {
  if (await window.appEnv.devMode()) {
    return "https://pouta-test.csc.fi:5001";
  } else {
    return "https://pouta.csc.fi:5001";
  }
}

export async function getSDConnectAPIEndpoint() {
  if (await window.appEnv.devMode()) {
    return "https://sd-connect.sdd.csc.fi";
  } else {
    return "https://sd-connect.sdqa.csc.fi";
  }
}

export const NEW_VERSION_DATE = Date.parse("2026-09-21T06:00:00Z");
