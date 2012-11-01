"""This module originally includes functions for grading Vsepr problems.

Also, may be this module is the place for other chemistry-related grade functions. TODO: discuss it.
"""

import json
import unittest
import itertools


def vsepr_parse_user_answer(user_input):
    """
    user_input is json generated by vsepr.js from dictionary.
    There are must be only two keys in original user_input dictionary: "geometry" and "atoms".
    Format: u'{"geometry": "AX3E0","atoms":{"c0": "B","p0": "F","p1": "B","p2": "F"}}'
    Order of elements inside "atoms" subdict does not matters.
    Return dict from parsed json.

    "Atoms" subdict stores positions of atoms in molecule.
    General types of positions:
        c0 - central atom
        p0..pN - peripheral atoms
        a0..aN - axial atoms
        e0..eN - equatorial atoms

    Each position is dictionary key, i.e. user_input["atoms"]["c0"] is central atom, user_input["atoms"]["a0"] is one of axial atoms.

    Special position only for AX6 (Octahedral) geometry:
        e10, e12  - atom pairs opposite the central atom,
        e20, e22  - atom pairs opposite the central atom,
        e1 and e2 pairs lying crosswise in equatorial plane.

    In user_input["atoms"] may be only 3 set of keys:
     (c0,p0..pN),
     (c0, a0..aN, e0..eN),
     (c0, a0, a1, e10,e11,e20,e21) - if geometry is AX6.
    """
    return json.loads(user_input)


def vsepr_build_correct_answer(geometry, atoms):
    """
    geometry is string.
    atoms is dict of atoms with proper positions.
    Example:

    correct_answer = vsepr_build_correct_answer(geometry="AX4E0", atoms={"c0": "N", "p0": "H", "p1": "(ep)", "p2": "H", "p3": "H"})

    returns a dictionary composed from input values:
         {'geometry': geometry, 'atoms': atoms}
    """
    return {'geometry': geometry, 'atoms': atoms}


def vsepr_grade(user_input, correct_answer, convert_to_peripheral=False):
    """
       This function does comparison between user_input and correct_answer.

       Comparison is successful if all steps are successful:

       1) geometries are equal
       2) central atoms (index in dictionary 'c0') are equal
       3):
        In next steps there is comparing of corresponding subsets of atom positions: equatorial (e0..eN), axial (a0..aN) or peripheral (p0..pN)

        If convert_to_peripheral is True, then axial and equatorial positions are converted to peripheral.
        This means that user_input from:
        "atoms":{"c0": "Br","a0": "test","a1": "(ep)","e10": "H","e11": "(ep)","e20": "H","e21": "(ep)"}}' after parsing to json
        is converted to:
        {"c0": "Br", "p0": "(ep)", "p1": "test", "p2": "H", "p3": "H", "p4": "(ep)", "p6": "(ep)"}
        i.e. aX and eX -> pX

        So if converted, p subsets are compared,
        if not a and e subsets are compared
        If all subsets are equal, grade succeeds.

        There is also one special case for AX6 geometry.
        In this case user_input["atoms"] contains special 3 symbol keys: e10, e12, e20, and e21.
        Correct answer for this geometry can be of 3 types:
        1) c0 and peripheral
        2) c0 and axial and equatorial
        3) c0 and axial and equatorial-subset-1 (e1X) and equatorial-subset-2 (e2X)

        If correct answer is type 1 or 2, then user_input is converted from type 3 to type 2 (or to type 1 if convert_to_peripheral is True)

        If correct_answer is type 3, then we done special case comparison. We have 3 sets of atoms positions both in user_input and correct_answer: axial, eq-1 and eq-2.
        Answer will be correct if these sets are equals for one of permutations. For example, if :
                user_axial = correct_eq-1
                user_eq-1 = correct-axial
                user_eq-2 = correct-eq-2

    """
    # import ipdb; ipdb.set_trace()
    # print user_input, type(user_input)
    # print correct_answer, type(correct_answer)
    if user_input['geometry'] != correct_answer['geometry']:
        return False

    if user_input['atoms']['c0'] != correct_answer['atoms']['c0']:
        return False

    if convert_to_peripheral:
        # convert user_input from (a,e,e1,e2) to (p)
        # correct_answer must be set in (p) using this flag
        c0 = user_input['atoms'].pop('c0')
        user_input['atoms'] = {'p' + str(i): v for i, v in enumerate(user_input['atoms'].values())}
        user_input['atoms']['c0'] = c0

    # special case for AX6
    if 'e10' in correct_answer['atoms']:  # need check e1x, e2x symmetry for AX6..
        a_user = {}
        a_correct = {}
        for ea_position in ['a', 'e1', 'e2']:  # collecting positions:
            a_user[ea_position] = [v for k, v in user_input['atoms'].items() if k.startswith(ea_position)]
            a_correct[ea_position] = [v for k, v in correct_answer['atoms'].items() if k.startswith(ea_position)]

        correct = [sorted(a_correct['a'])] + [sorted(a_correct['e1'])] + [sorted(a_correct['e2'])]
        for permutation in itertools.permutations(['a', 'e1', 'e2']):
            if correct == [sorted(a_user[permutation[0]])] + [sorted(a_user[permutation[1]])] + [sorted(a_user[permutation[2]])]:
                return True
        return False

    else:  # no need to check e1x,e2x symmetry - convert them to ex
        if 'e10' in user_input['atoms']:  # e1x exists, it is AX6.. case
            e_index = 0
            for k, v in user_input['atoms'].items():
                if len(k) == 3:  # e1x
                    del user_input['atoms'][k]
                    user_input['atoms']['e' + str(e_index)] = v
                    e_index += 1

        # common case
        for ea_position in ['p', 'a', 'e']:
            # collecting atoms:
            a_user = [v for k, v in user_input['atoms'].items() if k.startswith(ea_position)]
            a_correct = [v for k, v in correct_answer['atoms'].items() if k.startswith(ea_position)]
            # print a_user, a_correct
            if len(a_user) != len(a_correct):
                return False
            if sorted(a_user) != sorted(a_correct):
                return False

        return True


class Test_Grade(unittest.TestCase):
    ''' test grade function '''

    def test_incorrect_geometry(self):
        correct_answer = vsepr_build_correct_answer(geometry="AX4E0", atoms={"c0": "N", "p0": "H", "p1": "(ep)", "p2": "H", "p3": "H"})
        user_answer = vsepr_parse_user_answer(u'{"geometry": "AX3E0","atoms":{"c0": "B","p0": "F","p1": "B","p2": "F"}}')
        self.assertFalse(vsepr_grade(user_answer, correct_answer))

    def test_correct_answer_p(self):
        correct_answer = vsepr_build_correct_answer(geometry="AX4E0", atoms={"c0": "N", "p0": "H", "p1": "(ep)", "p2": "H", "p3": "H"})
        user_answer = vsepr_parse_user_answer(u'{"geometry": "AX4E0","atoms":{"c0": "N","p0": "H","p1": "(ep)","p2": "H", "p3": "H"}}')
        self.assertTrue(vsepr_grade(user_answer, correct_answer))

    def test_correct_answer_ae(self):
        correct_answer = vsepr_build_correct_answer(geometry="AX6E0", atoms={"c0": "Br", "a0": "test", "a1": "(ep)", "e0": "H", "e1": "H", "e2": "(ep)", "e3": "(ep)"})
        user_answer = vsepr_parse_user_answer(u'{"geometry": "AX6E0","atoms":{"c0": "Br","a0": "test","a1": "(ep)","e10": "H","e11": "H","e20": "(ep)","e21": "(ep)"}}')
        self.assertTrue(vsepr_grade(user_answer, correct_answer))

    def test_correct_answer_ae_convert_to_p_but_input_not_in_p(self):
        correct_answer = vsepr_build_correct_answer(geometry="AX6E0", atoms={"c0": "Br", "a0": "(ep)", "a1": "test", "e0": "H", "e1": "H", "e2": "(ep)", "e3": "(ep)"})
        user_answer = vsepr_parse_user_answer(u'{"geometry": "AX6E0","atoms":{"c0": "Br","a0": "test","a1": "(ep)","e10": "H","e11": "(ep)","e20": "H","e21": "(ep)"}}')
        self.assertFalse(vsepr_grade(user_answer, correct_answer, convert_to_peripheral=True))

    def test_correct_answer_ae_convert_to_p(self):
        correct_answer = vsepr_build_correct_answer(geometry="AX6E0", atoms={"c0": "Br", "p0": "(ep)", "p1": "test", "p2": "H", "p3": "H", "p4": "(ep)", "p6": "(ep)"})
        user_answer = vsepr_parse_user_answer(u'{"geometry": "AX6E0","atoms":{"c0": "Br","a0": "test","a1": "(ep)","e10": "H","e11": "(ep)","e20": "H","e21": "(ep)"}}')
        self.assertTrue(vsepr_grade(user_answer, correct_answer, convert_to_peripheral=True))

    def test_correct_answer_e1e2_in_a(self):
        correct_answer = vsepr_build_correct_answer(geometry="AX6E0", atoms={"c0": "Br", "a0": "(ep)", "a1": "(ep)", "e10": "H", "e11": "H", "e20": "H", "e21": "H"})
        user_answer = vsepr_parse_user_answer(u'{"geometry": "AX6E0","atoms":{"c0": "Br","a0": "(ep)","a1": "(ep)","e10": "H","e11": "H","e20": "H","e21": "H"}}')
        self.assertTrue(vsepr_grade(user_answer, correct_answer))

    def test_correct_answer_e1e2_in_e1(self):
        correct_answer = vsepr_build_correct_answer(geometry="AX6E0", atoms={"c0": "Br", "a0": "(ep)", "a1": "(ep)", "e10": "H", "e11": "H", "e20": "H", "e21": "H"})
        user_answer = vsepr_parse_user_answer(u'{"geometry": "AX6E0","atoms":{"c0": "Br","a0": "H","a1": "H","e10": "(ep)","e11": "(ep)","e20": "H","e21": "H"}}')
        self.assertTrue(vsepr_grade(user_answer, correct_answer))

    def test_correct_answer_e1e2_in_e2(self):
        correct_answer = vsepr_build_correct_answer(geometry="AX6E0", atoms={"c0": "Br", "a0": "(ep)", "a1": "(ep)", "e10": "H", "e11": "H", "e20": "H", "e21": "H"})
        user_answer = vsepr_parse_user_answer(u'{"geometry": "AX6E0","atoms":{"c0": "Br","a0": "H","a1": "H","e10": "H","e11": "H","e20": "(ep)","e21": "(ep)"}}')
        self.assertTrue(vsepr_grade(user_answer, correct_answer))

    def test_incorrect_answer_e1e2(self):
        correct_answer = vsepr_build_correct_answer(geometry="AX6E0", atoms={"c0": "Br", "a0": "(ep)", "a1": "(ep)", "e10": "H", "e11": "H", "e20": "H", "e21": "H"})
        user_answer = vsepr_parse_user_answer(u'{"geometry": "AX6E0","atoms":{"c0": "Br","a0": "H","a1": "H","e10": "(ep)","e11": "H","e20": "H","e21": "(ep)"}}')
        self.assertFalse(vsepr_grade(user_answer, correct_answer))

    def test_incorrect_c0(self):
        correct_answer = vsepr_build_correct_answer(geometry="AX6E0", atoms={"c0": "Br", "a0": "(ep)", "a1": "test", "e0": "H", "e1": "H", "e2": "H", "e3": "(ep)"})
        user_answer = vsepr_parse_user_answer(u'{"geometry": "AX6E0","atoms":{"c0": "H","a0": "test","a1": "(ep)","e0": "H","e1": "H","e2": "(ep)","e3": "H"}}')
        self.assertFalse(vsepr_grade(user_answer, correct_answer))


def suite():

    testcases = [Test_Grade]
    suites = []
    for testcase in testcases:
        suites.append(unittest.TestLoader().loadTestsFromTestCase(testcase))
    return unittest.TestSuite(suites)

if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2).run(suite())
