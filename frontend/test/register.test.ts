import { afterEach, describe, expect, it, vi } from "vitest";

/** A stand-in registry that records define() calls. */
function fakeRegistry(defined: string[] = []) {
  let resolveBoot: () => void = () => {};
  const boot = new Promise<void>((resolve) => {
    resolveBoot = resolve;
  });
  const names = new Set(defined);
  const registry = {
    defined: [] as string[],
    get: (name: string) => (names.has(name) ? class {} : undefined),
    define: (name: string) => {
      names.add(name);
      registry.defined.push(name);
    },
    whenDefined: () => boot,
    boot: () => resolveBoot(),
  };
  return registry;
}

const original = window.customElements;

function useRegistry(registry: unknown): void {
  Object.defineProperty(window, "customElements", { value: registry, configurable: true });
}

afterEach(() => {
  useRegistry(original);
  document.body.innerHTML = "";
  delete window.customCards;
  vi.resetModules();
});

describe("registration", () => {
  it("waits for the HA frontend to boot and defines in the final registry", async () => {
    // The page has the <home-assistant> root, not yet defined: the frontend is booting.
    document.body.appendChild(document.createElement("home-assistant"));
    const early = fakeRegistry();
    useRegistry(early);
    await import("../src/index");
    expect(early.defined).toEqual([]);

    // The frontend's registry polyfill replaces window.customElements while booting.
    const final = fakeRegistry(["home-assistant"]);
    useRegistry(final);
    early.boot();
    await Promise.resolve();
    await Promise.resolve();

    expect(early.defined).toEqual([]);
    expect(final.defined).toEqual(["energy-cost-stats-card"]);
    expect(window.customCards?.map((c) => c.type)).toEqual(["energy-cost-stats-card"]);
  });

  it("defines right away after boot (loaded as a dashboard resource)", async () => {
    document.body.appendChild(document.createElement("home-assistant"));
    const registry = fakeRegistry(["home-assistant"]);
    useRegistry(registry);
    await import("../src/index");
    expect(registry.defined).toEqual(["energy-cost-stats-card"]);
  });

  it("defines right away outside the HA page", async () => {
    const registry = fakeRegistry();
    useRegistry(registry);
    await import("../src/index");
    expect(registry.defined).toEqual(["energy-cost-stats-card"]);
  });

  it("does not define or announce twice", async () => {
    const registry = fakeRegistry();
    useRegistry(registry);
    const { defineCard } = await import("../src/index");
    defineCard();
    expect(registry.defined).toEqual(["energy-cost-stats-card"]);
    expect(window.customCards).toHaveLength(1);
  });
});
