import unittest, json
import numpy as np
from veritas import *

def update_bc(workspace, bc):
    bc.copy_from_workspace(workspace)
    i = 0
    while bc.update() == BoxCheckerUpdateResult.UPDATED:
        i += 1
        print("update", i)

class TestBoxChecker(unittest.TestCase):
    def test_copy_from_workspace(self):
        workspace = [(0, RealDomain(-1, 10)), (1, RealDomain(1, 2))]
        bc = BoxChecker(3, 5)

        self.assertTrue(bc.get_expr_dom(0).is_everything())
        self.assertTrue(bc.get_expr_dom(1).is_everything())
        self.assertTrue(bc.get_expr_dom(2).is_everything())

        bc.copy_from_workspace(workspace)

        self.assertEqual(bc.get_expr_dom(0), RealDomain(-1, 10))
        self.assertEqual(bc.get_expr_dom(1), RealDomain(1, 2))
        self.assertTrue(bc.get_expr_dom(2).is_everything())

        print(bc.get_expr_dom(0))
        print(bc.get_expr_dom(1))
        print(bc.get_expr_dom(2))

    def test_sum1(self):
        workspace = [(0, RealDomain(-1, 10)), (1, RealDomain(1, 2))]
        bc = BoxChecker(3, 5)
        s = bc.add_sum(0, 1)
        bc.add_eq(2, s)

        update_bc(workspace, bc)

        self.assertEqual(bc.get_expr_dom(0), RealDomain(-1, 10))
        self.assertEqual(bc.get_expr_dom(1), RealDomain(1, 2))
        self.assertEqual(bc.get_expr_dom(2), RealDomain(0, 12))

    def test_sum2(self):
        workspace = [(1, RealDomain(-1, 10)), (2, RealDomain(1, 2))]
        bc = BoxChecker(3, 5)
        s = bc.add_sum(0, 1)
        bc.add_eq(2, s)

        update_bc(workspace, bc)

        self.assertEqual(bc.get_expr_dom(0), RealDomain(-9, 3))
        self.assertEqual(bc.get_expr_dom(1), RealDomain(-1, 10))
        self.assertEqual(bc.get_expr_dom(2), RealDomain(1, 2))

    def test_sum3(self):
        workspace = [(2, RealDomain(1, 2))]
        bc = BoxChecker(3, 5)
        s = bc.add_sum(0, 1)
        bc.add_eq(2, s)

        update_bc(workspace, bc)

        self.assertTrue(bc.get_expr_dom(0).is_everything())
        self.assertTrue(bc.get_expr_dom(1).is_everything())
        self.assertEqual(bc.get_expr_dom(2), RealDomain(1, 2))

    def test_sub1(self):
        workspace = [(0, RealDomain(-1, 10)), (1, RealDomain(1, 2))]
        bc = BoxChecker(3, 5)
        s = bc.add_sub(0, 1)
        bc.add_eq(2, s)

        update_bc(workspace, bc)

        self.assertEqual(bc.get_expr_dom(0), RealDomain(-1, 10))
        self.assertEqual(bc.get_expr_dom(1), RealDomain(1, 2))
        self.assertEqual(bc.get_expr_dom(2), RealDomain(-3, 9))

    def test_prod1(self):
        workspace = [(0, RealDomain(-1, 10)), (1, RealDomain(1, 2))]
        bc = BoxChecker(3, 5)
        s = bc.add_prod(0, 1)
        bc.add_eq(2, s)

        update_bc(workspace, bc)

        self.assertEqual(bc.get_expr_dom(0), RealDomain(-1, 10))
        self.assertEqual(bc.get_expr_dom(1), RealDomain(1, 2))
        self.assertEqual(bc.get_expr_dom(2), RealDomain(-2, 20))

    def test_prod2(self):
        workspace = [(1, RealDomain(-1, 2)), (2, RealDomain(1, 2))]
        bc = BoxChecker(3, 5)
        s = bc.add_prod(0, 1)
        bc.add_eq(2, s)

        update_bc(workspace, bc)

        self.assertTrue(bc.get_expr_dom(0).is_everything()) # can become arbitrarily high because 0 in id1
        self.assertEqual(bc.get_expr_dom(1), RealDomain(-1, 2))
        self.assertEqual(bc.get_expr_dom(2), RealDomain(1, 2))

    def test_prod3(self):
        workspace = [(1, RealDomain(2, 4)), (2, RealDomain(-10, 20))]
        bc = BoxChecker(3, 5)
        s = bc.add_prod(0, 1)
        bc.add_eq(2, s)

        update_bc(workspace, bc)

        self.assertEqual(bc.get_expr_dom(0), RealDomain(-5, 10))
        self.assertEqual(bc.get_expr_dom(1), RealDomain(2, 4))
        self.assertEqual(bc.get_expr_dom(2), RealDomain(-10, 20))

    def test_div1(self):
        workspace = [(0, RealDomain(-1, 10)), (1, RealDomain(2, 4))]
        bc = BoxChecker(3, 5)
        s = bc.add_div(0, 1)
        bc.add_eq(2, s)

        update_bc(workspace, bc)

        self.assertEqual(bc.get_expr_dom(0), RealDomain(-1, 10))
        self.assertEqual(bc.get_expr_dom(1), RealDomain(2, 4))
        self.assertEqual(bc.get_expr_dom(2), RealDomain(-0.5, 5))

    def test_pow2_1(self):
        workspace = [(0, RealDomain(-1, 10))]
        bc = BoxChecker(2, 5)
        s = bc.add_pow2(0)
        bc.add_eq(1, s)

        update_bc(workspace, bc)

        self.assertEqual(bc.get_expr_dom(0), RealDomain(-1, 10))
        self.assertEqual(bc.get_expr_dom(1), RealDomain(0, 100))

    def test_pow2_2(self):
        workspace = [(0, RealDomain(1, 10))]
        bc = BoxChecker(2, 5)
        s = bc.add_pow2(0)
        bc.add_eq(1, s)

        update_bc(workspace, bc)

        self.assertEqual(bc.get_expr_dom(0), RealDomain(1, 10))
        self.assertEqual(bc.get_expr_dom(1), RealDomain(1, 100))

    def test_pow2_3(self):
        workspace = [(1, RealDomain(1, 100))]
        bc = BoxChecker(2, 5)
        s = bc.add_pow2(0)
        bc.add_eq(1, s)

        update_bc(workspace, bc)

        self.assertEqual(bc.get_expr_dom(0), RealDomain(-10, 10))
        self.assertEqual(bc.get_expr_dom(1), RealDomain(1, 100))

    def test_pow2_4(self):
        workspace = [(1, RealDomain(-10, 100))]
        bc = BoxChecker(2, 5)
        s = bc.add_pow2(0)
        bc.add_eq(1, s)

        update_bc(workspace, bc)

        self.assertEqual(bc.get_expr_dom(0), RealDomain(-10, 10))
        self.assertEqual(bc.get_expr_dom(1), RealDomain(0, 100))

    def test_sqrt1(self):
        workspace = [(0, RealDomain(-10, 100))]
        bc = BoxChecker(2, 5)
        s = bc.add_sqrt(0)
        bc.add_eq(1, s)

        update_bc(workspace, bc)

        self.assertEqual(bc.get_expr_dom(0), RealDomain(0, 100))
        self.assertEqual(bc.get_expr_dom(1), RealDomain(0, 10))

    def test_sqrt2(self):
        workspace = [(0, RealDomain(4, 100))]
        bc = BoxChecker(2, 5)
        s = bc.add_sqrt(0)
        bc.add_eq(1, s)

        update_bc(workspace, bc)

        self.assertEqual(bc.get_expr_dom(0), RealDomain(4, 100))
        self.assertEqual(bc.get_expr_dom(1), RealDomain(2, 10))

    def test_sqrt3(self):
        workspace = [(1, RealDomain(2, 10))]
        bc = BoxChecker(2, 5)
        s = bc.add_sqrt(0)
        bc.add_eq(1, s)

        update_bc(workspace, bc)

        self.assertEqual(bc.get_expr_dom(0), RealDomain(4, 100))
        self.assertEqual(bc.get_expr_dom(1), RealDomain(2, 10))

    def test_sqrt4(self):
        workspace = [(1, RealDomain(-10, 10))]
        bc = BoxChecker(2, 5)
        s = bc.add_sqrt(0)
        bc.add_eq(1, s)

        update_bc(workspace, bc)

        self.assertEqual(bc.get_expr_dom(0), RealDomain(0, 100))
        self.assertEqual(bc.get_expr_dom(1), RealDomain(0, 10))

    def test_binary1(self):
        workspace = [(0, TRUE_DOMAIN), (1, FALSE_DOMAIN)]
        bc = BoxChecker(3, 5)
        s = bc.add_k_out_of_n([0, 1, 2], 1, True)

        update_bc(workspace, bc)

        self.assertEqual(bc.get_expr_dom(0), TRUE_DOMAIN)
        self.assertEqual(bc.get_expr_dom(1), FALSE_DOMAIN)
        self.assertEqual(bc.get_expr_dom(2), FALSE_DOMAIN)

    def test_binary2(self):
        workspace = [(0, FALSE_DOMAIN), (1, FALSE_DOMAIN)]
        bc = BoxChecker(3, 5)
        s = bc.add_k_out_of_n([0, 1, 2], 1, True)

        update_bc(workspace, bc)

        self.assertEqual(bc.get_expr_dom(0), FALSE_DOMAIN)
        self.assertEqual(bc.get_expr_dom(1), FALSE_DOMAIN)
        self.assertEqual(bc.get_expr_dom(2), TRUE_DOMAIN)

    def test_binary3(self):
        workspace = [(0, FALSE_DOMAIN), (1, FALSE_DOMAIN)]
        bc = BoxChecker(3, 5)
        s = bc.add_at_least_k([0, 1, 2], 2)
        update_bc(workspace, bc)
        self.assertEqual(bc.update(), BoxCheckerUpdateResult.INVALID)

    def test_binary4(self):
        workspace = [(0, TRUE_DOMAIN), (1, TRUE_DOMAIN)]
        bc = BoxChecker(3, 5)
        s = bc.add_at_most_k([0, 1, 2], 1)
        update_bc(workspace, bc)
        self.assertEqual(bc.update(), BoxCheckerUpdateResult.INVALID)

    def test_complex1(self):
        workspace = [(0, RealDomain(2, 6)), (1, RealDomain(1, 9)), (2, RealDomain())]
        bc = BoxChecker(3, 5)
        s0 = bc.add_sub(0, 1)
        s1 = bc.add_pow2(s0)
        s2 = bc.add_sqrt(s1)

        bc.add_eq(s2, 2)
        update_bc(workspace, bc)

        #print(bc.get_expr_dom(0))
        #print(bc.get_expr_dom(1))
        #print(bc.get_expr_dom(2))
        #print("sub", bc.get_expr_dom(s0))
        #print("pow", bc.get_expr_dom(s1))
        #print("sqrt", bc.get_expr_dom(s2))

        self.assertEqual(bc.get_expr_dom(2), RealDomain(0, 7))

    def test_complex2(self):
        workspace = [
            (0, RealDomain(3, 5)), # x0
            (1, RealDomain(1, 7)), # x1
            (2, RealDomain(3, 4)), # y0
            (3, RealDomain(1, 2)), # y1
            (4, RealDomain(-1, 1)), # (x0-x1)/(sqrt((x0-x1)²+(y0-y1)²))
            (5, RealDomain(-1, 1)), # (y0-y1)/(sqrt((x0-x1)²+(y0-y1)²))
        ]
        bc = BoxChecker(len(workspace), 5)

        dx = bc.add_sub(0, 1)
        dy = bc.add_sub(2, 3)
        dx2 = bc.add_pow2(dx)
        dy2 = bc.add_pow2(dy)
        dx2dy2 = bc.add_sum(dx2, dy2)
        sqrt = bc.add_sqrt(dx2dy2)
        dxdiv = bc.add_div(dx, sqrt)
        dydiv = bc.add_div(dy, sqrt)

        bc.add_eq(dxdiv, 4)
        bc.add_eq(dydiv, 5)
        update_bc(workspace, bc)

        bc.add_lteq(dx, sqrt)
        bc.add_lteq(dy, sqrt)

        print("x0", bc.get_expr_dom(0))
        print("x1", bc.get_expr_dom(1))
        print("x2", bc.get_expr_dom(2))
        print("x3", bc.get_expr_dom(3))
        print("nx", bc.get_expr_dom(4))
        print("ny", bc.get_expr_dom(5))

        print()
        print("dx", bc.get_expr_dom(dx))
        print("dy", bc.get_expr_dom(dy))
        print("dx2", bc.get_expr_dom(dx2))
        print("dy2", bc.get_expr_dom(dy2))
        print("dx2dy2", bc.get_expr_dom(dx2dy2))
        print("sqrt", bc.get_expr_dom(sqrt))

        self.assertEqual(bc.get_expr_dom(dxdiv), RealDomain(-1, 1))
        self.assertEqual(bc.get_expr_dom(dydiv), RealDomain(0.2, 1))
        self.assertEqual(bc.get_expr_dom(sqrt), RealDomain(1, 5))

if __name__ == "__main__":
    unittest.main()
