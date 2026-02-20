import pytest
from mako.lookup import TemplateLookup
from mako.exceptions import SyntaxException

from promptdepot.renderers.mako import MakoPromptRenderer, MakoPromptRendererConfig


@pytest.fixture
def simple_template() -> str:
    return "Hello ${name}!"


@pytest.fixture
def simple_config() -> MakoPromptRendererConfig:
    return {"lookup": None}


@pytest.fixture
def config_with_lookup(tmp_path) -> MakoPromptRendererConfig:
    lookup = TemplateLookup(directories=[str(tmp_path)])
    return {"lookup": lookup}


def test_mako_prompt_renderer_init__should_set_template_and_config(
    simple_template: str,
    simple_config: MakoPromptRendererConfig,
):
    renderer = MakoPromptRenderer(template=simple_template, config=simple_config)

    assert renderer.template == simple_template
    assert renderer.config == simple_config


def test_mako_prompt_renderer_init__should_compile_template(
    simple_template: str,
    simple_config: MakoPromptRendererConfig,
):
    renderer = MakoPromptRenderer(template=simple_template, config=simple_config)

    assert renderer.compiled_template is not None
    assert hasattr(renderer.compiled_template, "render")


def test_mako_prompt_renderer_init__should_raise_on_invalid_template_syntax():
    invalid_template = "${unclosed"
    config: MakoPromptRendererConfig = {"lookup": None}

    with pytest.raises(SyntaxException):
        MakoPromptRenderer(template=invalid_template, config=config)


def test_mako_prompt_renderer_init__should_accept_lookup_in_config(
    simple_template: str,
    config_with_lookup: MakoPromptRendererConfig,
):
    renderer = MakoPromptRenderer(template=simple_template, config=config_with_lookup)

    assert renderer.config["lookup"] is not None
    assert isinstance(renderer.config["lookup"], TemplateLookup)


def test_mako_prompt_renderer_from_template__should_create_instance_correctly(
    simple_template: str,
    simple_config: MakoPromptRendererConfig,
):
    renderer = MakoPromptRenderer.from_template(
        template=simple_template, config=simple_config
    )

    assert isinstance(renderer, MakoPromptRenderer)
    assert renderer.template == simple_template
    assert renderer.config == simple_config
    assert renderer.compiled_template is not None


def test_mako_prompt_renderer_render__should_render_simple_template(
    simple_template: str,
    simple_config: MakoPromptRendererConfig,
):
    renderer = MakoPromptRenderer(template=simple_template, config=simple_config)

    result = renderer.render(context={"name": "World"})

    assert result == "Hello World!"


def test_mako_prompt_renderer_render__should_render_with_empty_context():
    template = "Hello static text"
    config: MakoPromptRendererConfig = {"lookup": None}
    renderer = MakoPromptRenderer(template=template, config=config)

    result = renderer.render(context={})

    assert result == "Hello static text"


def test_mako_prompt_renderer_render__should_render_with_multiple_variables():
    template = "Hello ${name}, you are ${age} years old"
    config: MakoPromptRendererConfig = {"lookup": None}
    renderer = MakoPromptRenderer(template=template, config=config)

    result = renderer.render(context={"name": "Alice", "age": 30})

    assert result == "Hello Alice, you are 30 years old"
