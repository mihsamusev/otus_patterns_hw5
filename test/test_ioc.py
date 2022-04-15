import unittest
from dataclasses import dataclass

from src.ioc import IoC


class TestIoCRootScope(unittest.TestCase):
    def test_ioc_raises_if_no_dependency_found(self):
        with IoC.resolve("scopes.create", "root").execute():
            self.assertRaises(Exception, IoC.resolve, args=("unknownkey", "arg1", 42))

    def test_ioc_root_scope_registers_and_resolves_primitives(self):
        with IoC.resolve("scopes.create", "root").execute():
            cases = [
                ("number", 34234),
                ("data_structure_1", {"key": "value"}),
                ("data_structure_2", [(1.5, 2.5), (-2.4, -1000.0)]),
            ]

            # assign free variable value at definition time, not execution time
            for key, value in cases:
                IoC.resolve("ioc.register", key, lambda v=value: v).execute()

            for key, expected in cases:
                result = IoC.resolve(key)
                self.assertEqual(result, expected)

    def test_ioc_root_scope_registers_and_resolves_by_reference(self):
        with IoC.resolve("scopes.create", "root").execute():
            singleton_object = {"config": 0, "data": "data"}
            IoC.resolve("ioc.register", "singleton", lambda: singleton_object).execute()

            singleton_object["config"] = 1
            singleton_object["new_data"] = "new_data"

            result = IoC.resolve("singleton")
            self.assertEqual(id(singleton_object), id(result))
            self.assertEqual(singleton_object, result)

    def test_ioc_root_scope_registers_and_resolves_class_constructor_to_unique_objects(
        self,
    ):
        @dataclass
        class Entity:
            name: str
            id: int

        with IoC.resolve("scopes.create", "root").execute():
            IoC.resolve(
                "ioc.register", "Entity_1", lambda *args: Entity(*args)
            ).execute()

            result1 = IoC.resolve("Entity_1", "e1", 1)
            result2 = IoC.resolve("Entity_1", "e2", 2)

            self.assertEqual(Entity(name="e1", id=1), result1)
            self.assertEqual(Entity(name="e2", id=2), result2)

    def test_ioc_root_scope_registers_and_resolves_by_both_lambda_and_function_reference(
        self,
    ):
        def get_list():
            return ["id_1", "id_2"]

        with IoC.resolve("scopes.create", "root").execute():
            IoC.resolve("ioc.register", "list_1", lambda: ["id_1", "id_2"]).execute()
            IoC.resolve("ioc.register", "list_2", get_list).execute()

            self.assertEqual(IoC.resolve("list_1"), IoC.resolve("list_2"))


class TestIoCMultiScope(unittest.TestCase):
    def test_registering_value_in_child_scope_does_not_affect_parent(self):
        with IoC.resolve("scopes.create", "root").execute() as test_root:
            new_scope = IoC.resolve("scopes.create", test_root.name).execute()
            IoC.resolve("scopes.set", new_scope.name).execute()
            # with IoC.resolve("scopes.create_and_set", "root"):

            IoC.resolve("ioc.register", "data_new", lambda: {"key", "value"}).execute()
            self.assertEqual(IoC.resolve("data_new"), {"key", "value"})

            IoC.resolve("scopes.set", test_root.name).execute()
            self.assertRaises(Exception, IoC.resolve, "data_new")

    def test_context_manager_sets_new_scope_within_context(self):
        with IoC.resolve("scopes.create", "root").execute() as test_root:
            with IoC.resolve("scopes.create", test_root.name).execute():
                IoC.resolve(
                    "ioc.register", "data_new", lambda: {"key", "value"}
                ).execute()
                self.assertEqual(IoC.resolve("data_new"), {"key", "value"})

            self.assertEqual(test_root, IoC.resolve("scopes.current"))
            self.assertRaises(Exception, IoC.resolve, "data_new")

    def test_context_manager_works_with_interrupted_named_scope(self):
        with IoC.resolve("scopes.create", "root").execute() as test_root:
            with IoC.resolve("scopes.create", test_root.name, "my_scope").execute():
                IoC.resolve(
                    "ioc.register", "data_new", lambda: {"key", "value"}
                ).execute()

            self.assertRaises(Exception, IoC.resolve, "data_new")

            with IoC.resolve("scopes.set", "my_scope").execute():
                self.assertEqual(IoC.resolve("data_new"), {"key", "value"})

            self.assertRaises(Exception, IoC.resolve, "data_new")
