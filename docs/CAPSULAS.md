# Cápsulas errantes — contrato de diseño

En *Zero History* ninguna cápsula tiene una posición fija. Cada etapa tiene
**tres nichos** autorados (los tres alcanzables con el equipo base) y cada
partida elige uno por etapa y reparte los ocho contenidos al azar.

La implementación de referencia, ejecutable y probada, es
[`tools/capsule_shuffle.py`](../tools/capsule_shuffle.py); sus pruebas están en
[`tools/test_capsule_shuffle.py`](../tools/test_capsule_shuffle.py).

## Contenidos

Ocho ítems, uno por etapa:

- **Botas** — salto y dash aéreo.
- **Armadura** — daño reducido.
- **Casco** — rompe bloques.
- **Buster** — carga doble.
- **Sable Zero** — habilita jugar como Zero.
- **Núcleo 01/02/03** — fragmentos de memoria (historia).

## Las cuatro garantías

1. **Biyectividad.** Cada una de las ocho etapas tiene exactamente una cápsula,
   y cada uno de los ocho ítems aparece exactamente una vez. Si falta uno, el
   jugador pierde un fragmento de historia que no puede recuperar.
2. **Alcanzabilidad.** El barajado solo elige entre los tres nichos autorados de
   cada etapa. Nunca inventa una posición, así que ningún ítem puede caer donde
   el jugador no puede llegar.
3. **Determinismo.** La misma semilla produce siempre el mismo reparto. Una
   semilla publicada en un foro reproduce la partida exacta.
4. **Sin callejón sin salida.** Ningún ítem es requisito para alcanzar ningún
   nicho, y el anillo de debilidades de los jefes se cierra: cualquier orden de
   etapas es jugable hasta el final.

## Modos y semilla

- **Historia** — la semilla se deriva de `perfil + slot + número de partida`,
  así que cada partida nueva baraja distinto pero es reproducible. La semilla
  se muestra en el select de etapas.
- **Speedrun** — semilla fija `0`. Todos los corredores juegan el mismo reparto.
- **Caos** — semilla aleatoria en cada partida, también visible.

```console
$ python3 tools/capsule_shuffle.py --mode speedrun
semilla 00000000
  W-01 condor_cobalto   nicho 3  -> Casco      (rompe bloques)
  W-02 salitre_sierpe   nicho 2  -> Núcleo 01  (fragmento de memoria)
  ...

$ python3 tools/capsule_shuffle.py --mode historia --slot 1
semilla CC0D3F32
  ...
```

## Por qué un barajado y no un random por ítem

Un sorteo independiente por ítem puede repetir contenido o dejar una etapa
vacía. Ambas cosas rompen la garantía 1. El barajado de una lista completa es
la construcción más simple que la cumple por diseño, y `validate()` la verifica
en cada llamada en vez de confiar en que el código esté bien.

## Estado de integración

El módulo es la **especificación ejecutable** del sistema: define semillas,
reparto y pruebas. Todavía no está conectado al ejecutable, porque hacerlo
requiere mover la lógica de cápsulas dentro del ROM recompilado (tabla de
objetos por etapa + un hook de lectura de la semilla). Ver
[`ESTADO.md`](ESTADO.md).
