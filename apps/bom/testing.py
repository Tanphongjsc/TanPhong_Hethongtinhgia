"""Inspected trigger behavior, installed only in isolated test_costing_slice."""


def install_recipe_triggers(editor):
    if editor.connection.settings_dict["NAME"] != "test_costing_slice" or editor.connection.settings_dict["HOST"] != "127.0.0.1":
        raise RuntimeError("Recipe fixture DDL is restricted to isolated localhost tests.")
    editor.execute("""
        CREATE FUNCTION public.test_recipe_version_immutable() RETURNS trigger
        LANGUAGE plpgsql SET search_path TO '' AS $$
        BEGIN
            IF OLD.status IN ('APPROVED','EFFECTIVE','RETIRED') THEN
                RAISE EXCEPTION 'Immutable recipe version';
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END; $$
    """)
    editor.execute("""
        CREATE TRIGGER trg_recipe_version_immutable BEFORE UPDATE OR DELETE
        ON public.recipe_version FOR EACH ROW EXECUTE FUNCTION public.test_recipe_version_immutable()
    """)
    editor.execute("""
        CREATE FUNCTION public.test_recipe_line_protect() RETURNS trigger
        LANGUAGE plpgsql SET search_path TO '' AS $$
        DECLARE v_status text; v_parent_id bigint;
        BEGIN
            v_parent_id := CASE WHEN TG_OP='DELETE' THEN OLD.recipe_version_id ELSE NEW.recipe_version_id END;
            SELECT status INTO v_status FROM public.recipe_version WHERE id=v_parent_id;
            IF v_status IN ('APPROVED','EFFECTIVE','RETIRED') THEN
                RAISE EXCEPTION 'Immutable recipe line';
            END IF;
            IF TG_OP='DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END; $$
    """)
    editor.execute("""
        CREATE TRIGGER trg_recipe_line_protect BEFORE INSERT OR UPDATE OR DELETE
        ON public.recipe_line FOR EACH ROW EXECUTE FUNCTION public.test_recipe_line_protect()
    """)


def install_packaging_triggers(editor):
    if editor.connection.settings_dict["NAME"] != "test_costing_slice" or editor.connection.settings_dict["HOST"] != "127.0.0.1":
        raise RuntimeError("Packaging fixture DDL is restricted to isolated localhost tests.")
    # Same inspected immutable-version function as Recipe; no production DDL.
    editor.execute("""
        CREATE TRIGGER trg_packaging_version_immutable BEFORE UPDATE OR DELETE
        ON public.packaging_config_version FOR EACH ROW EXECUTE FUNCTION public.test_recipe_version_immutable()
    """)
    editor.execute("""
        CREATE FUNCTION public.test_packaging_line_protect() RETURNS trigger
        LANGUAGE plpgsql SET search_path TO '' AS $$
        DECLARE v_status text; v_parent_id bigint;
        BEGIN
            v_parent_id := CASE WHEN TG_OP='DELETE' THEN OLD.packaging_config_version_id ELSE NEW.packaging_config_version_id END;
            SELECT status INTO v_status FROM public.packaging_config_version WHERE id=v_parent_id;
            IF v_status IN ('APPROVED','EFFECTIVE','RETIRED') THEN
                RAISE EXCEPTION 'Immutable packaging line';
            END IF;
            IF TG_OP='DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END; $$
    """)
    editor.execute("""
        CREATE TRIGGER trg_packaging_line_protect BEFORE INSERT OR UPDATE OR DELETE
        ON public.packaging_line FOR EACH ROW EXECUTE FUNCTION public.test_packaging_line_protect()
    """)


def install_routing_triggers(editor):
    if editor.connection.settings_dict["NAME"] != "test_costing_slice" or editor.connection.settings_dict["HOST"] != "127.0.0.1":
        raise RuntimeError("Routing fixture DDL is restricted to isolated localhost tests.")
    editor.execute("""
        CREATE TRIGGER trg_routing_version_immutable BEFORE UPDATE OR DELETE
        ON public.routing_version FOR EACH ROW EXECUTE FUNCTION public.test_recipe_version_immutable()
    """)
    editor.execute("""
        CREATE FUNCTION public.test_routing_operation_protect() RETURNS trigger
        LANGUAGE plpgsql SET search_path TO '' AS $$
        DECLARE v_status text; v_parent_id bigint;
        BEGIN
            v_parent_id := CASE WHEN TG_OP='DELETE' THEN OLD.routing_version_id ELSE NEW.routing_version_id END;
            SELECT status INTO v_status FROM public.routing_version WHERE id=v_parent_id;
            IF v_status IN ('APPROVED','EFFECTIVE','RETIRED') THEN
                RAISE EXCEPTION 'Immutable routing operation';
            END IF;
            IF TG_OP='DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END; $$
    """)
    editor.execute("""
        CREATE TRIGGER trg_routing_operation_protect BEFORE INSERT OR UPDATE OR DELETE
        ON public.routing_operation FOR EACH ROW EXECUTE FUNCTION public.test_routing_operation_protect()
    """)
