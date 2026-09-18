/**
 * Node draait de TypeScript van dit project rechtstreeks (type stripping), maar
 * verwacht dan volledige bestandsnamen in een import. De modules hier zijn
 * geschreven voor de bundler van Next en laten de extensie weg ("./format").
 * Deze resolver vult die aan, zodat de testrunner exact dezelfde bronbestanden
 * laadt als de applicatie — zonder aan de imports te sleutelen voor de test.
 */
export async function resolve(specifier, context, nextResolve) {
  const relatief = /^\.{1,2}\//.test(specifier);
  const heeftExtensie = /\.[cm]?[jt]sx?$/.test(specifier);
  if (relatief && !heeftExtensie) {
    try {
      return await nextResolve(`${specifier}.ts`, context);
    } catch {
      // Geen .ts ernaast: laat de gewone resolutie haar eigen fout geven.
    }
  }
  return nextResolve(specifier, context);
}
