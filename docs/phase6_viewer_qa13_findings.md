# Gate 4: QA-13-1 and QA-12b-1 identified by pixel pick - evidence only, nothing changed

QA-13-1, the blue intercolumniations at cam01.  Picked four representative pixels in the
band 20 520 540 645 (17.6 % of it is B > R+20 in the current capture).  What is under them:

  (48,567)  rgba 65/84/127   ENV_backdropgroup_backdrop_building
                             mat MAT_EXP_ENVBD__MAT_backdrop_building
                             uv1 FALSE, lightMap NULL, patched NULL, envMap false
  (174,603) rgba 155/153/195 ENV_backdropgroup_backdrop_skylight, same state
  (430,520) rgba 126/144/158 NOTHING DRAWN - this is the sky seen through the colonnade

So the blue rectangles are the ENV BACKDROP CITY BLOCKS seen through the north
intercolumniations, not a colonnade surface.  env.glb carries no TEXCOORD_1 at all, so no
lightmap can ever attach to them; they are not among the bake's 16 own-map assets; and
because nothing patched them they stay on the environment-lit path.  That is why they are
bit-identical with the lightmaps off: they never had one.

WHICH SIDE OWNS IT - the lighting, not the albedo, and the evidence is a grey-material pass:
with the albedo replaced by neutral grey the same pixel reads 55/97/205, MORE saturated
blue, so the blue is the incident light.  scene.environment is the DIFFUSE sky PMREM
(QA-12b-1's own change at Gate 3), and for an unpatched surface that is nearly all the
light it gets.  That also explains 3.9 % at Gate 2 -> 23.0 % now: at Gate 2 the environment
was the GLOSSY equirect; making it the diffuse branch made every unpatched surface bluer.
Two ways out, and it is the lead's call: give the backdrop group UV2 + a lightmap
(export + bake), or put unpatched surfaces on a real direct path in the viewer.  I have
changed nothing.

QA-12b-1, the olive cast at cam02.  Decomposed three olive building pixels three ways
(materials=pbr, materials=grey, and pbr with lut=0):

  (982,149)  ORN attic figure, slot lightmap   pbr 140/145/125   grey  56/87/169
  (1310,766) ARCH_rotunda_concrete_podium      pbr  52/57/46     grey  34/48/78
  (716,722)  ARCH_rotunda_concrete_ochre       pbr  84/93/69     nolut 94/102/84

Every one has uv1 true, a lightmap attached and patched with specularOnlySun +
noEnvDiffuse, so the live environment is NOT reaching them - the diffuse they get is the
LIGHTMAP TEXEL.  With a neutral grey albedo two of the three read BLUE (56/87/169,
34/48/78): the baked irradiance itself is blue in shade.  Turning the LUT off leaves the
hue where it was (94/102/84 is still G > R), so the transform is not making it either.

THE FACTOR THAT CARRIES THE GREEN IS THE ENVIRONMENT TERM INSIDE THE BAKE, and the
mechanism is manifest lightmaps.bake.color = FALSE.  A Cycles DIFFUSE bake with colour off
integrates the light against a WHITE albedo, so the indirect bounce loses the warm colour
bleed a real ochre courtyard has; the texel is sky-blue in shade where Cycles' beauty pass
has warm inter-reflection.  three then multiplies that bluer irradiance by the warm ochre
albedo, and warm albedo x blue light peaks in GREEN - the olive.  It is not the albedo bake
(grey is bluer, not greener) and not the LUT.  Bake-side fix: bake the diffuse with colour
ON and do not multiply the albedo again in the shader, or bake a separate coloured indirect.

The sunlit-attic saturation (0.94x -> 0.89x) is CONSISTENT with the same cause - neutral
baked indirect mixed into a saturated albedo loses chroma - but I have NOT isolated it, and
at cam01 I separately measured bloom taking that box from 0.49 to 0.44, so there are two
candidate contributors and I am not claiming which dominates.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
