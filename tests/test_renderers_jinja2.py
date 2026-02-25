import pytest
from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError

from promptdepot.renderers.jinja2 import (
    Jinja2PromptRenderer,
    Jinja2PromptRendererConfig,
)


@pytest.fixture
def simple_template() -> str:
    return "Hello {{ name }}!"


@pytest.fixture
def simple_config() -> Jinja2PromptRendererConfig:
    return {"environment": None}


@pytest.fixture
def config_with_environment(tmp_path) -> Jinja2PromptRendererConfig:
    environment = Environment(loader=FileSystemLoader(str(tmp_path)), autoescape=True)
    return {"environment": environment}


def test_jinja2_prompt_renderer_init__should_set_template_and_config(
    simple_template: str,
    simple_config: Jinja2PromptRendererConfig,
):
    renderer = Jinja2PromptRenderer(template=simple_template, config=simple_config)

    assert renderer.template == simple_template
    assert renderer.config == simple_config


def test_jinja2_prompt_renderer_init__should_compile_template(
    simple_template: str,
    simple_config: Jinja2PromptRendererConfig,
):
    renderer = Jinja2PromptRenderer(template=simple_template, config=simple_config)

    assert renderer.compiled_template is not None
    assert hasattr(renderer.compiled_template, "render")


def test_jinja2_prompt_renderer_init__should_raise_on_invalid_template_syntax():
    invalid_template = "{{ unclosed"
    config: Jinja2PromptRendererConfig = {"environment": None}

    with pytest.raises(TemplateSyntaxError):
        Jinja2PromptRenderer(template=invalid_template, config=config)


def test_jinja2_prompt_renderer_init__should_accept_environment_in_config(
    simple_template: str,
    config_with_environment: Jinja2PromptRendererConfig,
):
    renderer = Jinja2PromptRenderer(
        template=simple_template, config=config_with_environment
    )

    assert renderer.config["environment"] is not None
    assert isinstance(renderer.config["environment"], Environment)


def test_jinja2_prompt_renderer_from_template__should_create_instance_correctly(
    simple_template: str,
    simple_config: Jinja2PromptRendererConfig,
):
    renderer = Jinja2PromptRenderer.from_template(
        template=simple_template, config=simple_config
    )

    assert isinstance(renderer, Jinja2PromptRenderer)
    assert renderer.template == simple_template
    assert renderer.config == simple_config
    assert renderer.compiled_template is not None


def test_jinja2_prompt_renderer_render__should_render_simple_template(
    simple_template: str,
    simple_config: Jinja2PromptRendererConfig,
):
    renderer = Jinja2PromptRenderer(template=simple_template, config=simple_config)

    result = renderer.render(context={"name": "World"})

    assert result == "Hello World!"


def test_jinja2_prompt_renderer_render__should_render_with_empty_context():
    template = "Hello static text"
    config: Jinja2PromptRendererConfig = {"environment": None}
    renderer = Jinja2PromptRenderer(template=template, config=config)

    result = renderer.render(context={})

    assert result == "Hello static text"


def test_jinja2_prompt_renderer_render__should_render_with_multiple_variables():
    template = "Hello {{ name }}, you are {{ age }} years old"
    config: Jinja2PromptRendererConfig = {"environment": None}
    renderer = Jinja2PromptRenderer(template=template, config=config)

    result = renderer.render(context={"name": "Alice", "age": 30})

    assert result == "Hello Alice, you are 30 years old"
