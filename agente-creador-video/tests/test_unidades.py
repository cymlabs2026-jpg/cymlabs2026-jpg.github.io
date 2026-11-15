from pathlib import Path

from agente_video import tiempo
from agente_video.config import aplicar_glosario
from agente_video.etapas import guion, subtitulos
from agente_video.etapas.entrega import capitulos_finales


def test_plan_acelera_esperas_y_corta_tiempo_muerto():
    # 0–10 habla · 10–20 silencio con pantalla en movimiento · 20–30 silencio y pantalla quieta · 30–40 habla
    plan = tiempo.construir_plan(40, [(10, 30)], [(20, 30)], velocidad_espera=4, margen_s=0)
    assert [(t["inicio"], t["fin"], t["tipo"]) for t in plan] == [
        (0, 10, "normal"),
        (10, 20, "acelerar"),
        (20, 30, "cortar"),
        (30, 40, "normal"),
    ]
    assert tiempo.duracion_final(plan) == 10 + 2.5 + 0 + 10


def test_plan_respeta_margen_e_ignora_silencios_cortos():
    plan = tiempo.construir_plan(20, [(5, 5.8), (10, 14)], [], margen_s=0.5)
    especiales = [t for t in plan if t["tipo"] != "normal"]
    assert especiales == [{"inicio": 10.5, "fin": 13.5, "tipo": "acelerar", "velocidad": 4.0}]


def test_remapear():
    plan = tiempo.construir_plan(40, [(10, 30)], [(20, 30)], velocidad_espera=4, margen_s=0)
    assert tiempo.remapear(5, plan) == 5
    assert tiempo.remapear(14, plan) == 11  # 10 + 4/4
    assert tiempo.remapear(25, plan) == 12.5  # dentro del corte: salta al final del tramo anterior
    assert tiempo.remapear(35, plan) == 17.5
    assert tiempo.remapear(99, plan) == 22.5


def test_formatos_de_tiempo():
    assert tiempo.a_srt(3723.4567) == "01:02:03,457"
    assert tiempo.a_youtube(65) == "1:05"
    assert tiempo.a_youtube(3723) == "1:02:03"
    assert tiempo.de_marca(tiempo.a_marca(83.4)) == 83.4


def test_glosario_palabra_completa():
    glosario = {"Cloud": "Claude", "scroll y teller": "Scrollyteller"}
    assert aplicar_glosario("Cloud acaba de agregar", glosario) == "Claude acaba de agregar"
    assert aplicar_glosario("en el estilo scroll y teller", glosario) == "en el estilo Scrollyteller"
    assert aplicar_glosario("Cloudflare", glosario) == "Cloudflare"


def test_guion_markdown_ida_y_vuelta():
    original = {
        "titulos": ["Claude Sheets en 6 minutos", "Otro título"],
        "descripcion": "Aprende a usar las tres herramientas.\n\nSegundo párrafo.",
        "prompts": ["Voy a lanzar un curso online.\nOrdénalo por semana."],
        "capitulos": [{"inicio": 0.0, "titulo": "Intro"}, {"inicio": 18.3, "titulo": "Qué son los artefactos"}],
        "narracion": [
            {"inicio": 0.0, "fin": 7.2, "texto": "Claude acaba de agregar tres herramientas."},
            {"inicio": 7.2, "fin": 12.0, "texto": ""},
        ],
    }
    texto = guion.a_markdown(original, Path("/tmp/x"))
    assert guion.de_markdown(texto) == original


def test_guion_editado_a_mano():
    texto = guion.a_markdown(guion.guion_basico([{"inicio": 1.0, "fin": 3.0, "texto": "hola eh mundo"}]), Path("."))
    texto = texto.replace("hola eh mundo", "Hola, mundo.")
    datos = guion.de_markdown(texto)
    assert datos["narracion"][0]["texto"] == "Hola, mundo."
    assert datos["capitulos"] == [] and datos["titulos"] == [] and datos["descripcion"] == ""


def test_subtitulos_se_parten_y_remapean():
    plan = tiempo.construir_plan(40, [(10, 30)], [(20, 30)], velocidad_espera=4, margen_s=0)
    largo = "palabra " * 30
    srt = subtitulos.generar_srt(
        [{"inicio": 0, "fin": 8, "texto": largo}, {"inicio": 21, "fin": 29, "texto": "en el corte"},
         {"inicio": 30, "fin": 34, "texto": "Final."}],
        plan,
    )
    assert srt.count("-->") == 4  # 3 trozos del texto largo + "Final."; lo que cae en el corte no aparece
    assert "00:00:12,500 --> 00:00:16,500\nFinal." in srt
    for linea in srt.splitlines():
        assert len(linea) <= subtitulos.CARACTERES_POR_LINEA


def test_capitulos_reglas_de_youtube():
    plan = [{"inicio": 0, "fin": 300, "tipo": "normal", "velocidad": 1.0}]
    caps = [{"inicio": 2, "titulo": "Intro"}, {"inicio": 60, "titulo": "Paso 1"},
            {"inicio": 65, "titulo": "Muy cerca"}, {"inicio": 120, "titulo": "Paso 2"}]
    finales, avisos = capitulos_finales(caps, plan, 300)
    assert [(c["inicio"], c["titulo"]) for c in finales] == [(0.0, "Intro"), (60, "Paso 1"), (120, "Paso 2")]
    assert len(avisos) == 1


def test_respuesta_de_claude_a_guion():
    from agente_video.proveedores.llm import CapituloIA, GuionIA, SegmentoLimpio, a_guion

    segmentos = [{"inicio": 0.4, "fin": 7.0, "texto": "eh Cloud acaba de"}, {"inicio": 19.0, "fin": 28.0, "texto": "los artefactos"}]
    respuesta = GuionIA(
        titulos=["A", "B", "C"], descripcion=" Desc ", prompts=["p1", " "],
        capitulos=[CapituloIA(segmento=1, titulo="Artefactos"), CapituloIA(segmento=0, titulo="Intro"),
                   CapituloIA(segmento=9, titulo="Inexistente")],
        segmentos=[SegmentoLimpio(id=0, texto="Claude acaba de")],
    )
    guion = a_guion(respuesta, segmentos)
    assert guion["capitulos"] == [{"inicio": 0.0, "titulo": "Intro"}, {"inicio": 19.0, "titulo": "Artefactos"}]
    assert [b["texto"] for b in guion["narracion"]] == ["Claude acaba de", "los artefactos"]
    assert guion["prompts"] == ["p1"] and guion["descripcion"] == "Desc"
