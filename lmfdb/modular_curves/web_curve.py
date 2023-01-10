# -*- coding: utf-8 -*-

from collections import Counter
from flask import url_for

from sage.all import lazy_attribute, prod, euler_phi, ZZ, QQ, latex, PolynomialRing, lcm, NumberField
from sage.databases.cremona import class_to_int
from lmfdb.utils import WebObj, integer_prime_divisors, teXify_pol, web_latex, pluralize, display_knowl
from lmfdb import db
from lmfdb.classical_modular_forms.main import url_for_label as url_for_mf_label
from lmfdb.elliptic_curves.web_ec import latex_equation as EC_equation
from lmfdb.elliptic_curves.elliptic_curve import url_for_label as url_for_EC_label
from lmfdb.ecnf.main import url_for_label as url_for_ECNF_label
from lmfdb.number_fields.number_field import url_for_label as url_for_NF_label
from lmfdb.groups.abstract.main import abstract_group_display_knowl
from string import ascii_lowercase

def get_bread(tail=[]):
    base = [("Modular curves", url_for(".index")), (r"$\Q$", url_for(".index_Q"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail

def showexp(c, wrap=True):
    if c == 1:
        return ""
    elif wrap:
        return f"$^{{{c}}}$"
    else:
        return f"^{{{c}}}"

def showj(j):
    if j is None:
        return ""
    elif "/" in j:
        return r"$\tfrac{%s}{%s}$" % tuple(j.split("/"))
    else:
        return f"${j}$"

def showj_fac(j):
    j = QQ(j)
    if j == 0 or j.denominator() == 1 and j.numerator().is_prime():
        return ""
    else:
        return "$= %s$" % latex(j.factor())

def showj_nf(j, jfield, jorig, resfield):
    if j is None:
        return ""
    Ra = PolynomialRing(QQ, 'a')
    if "," in j:
        s = None
        f = Ra([QQ(c) for c in j.split(",")])
        if jfield.startswith("2."):
            D = ZZ(jfield.split(".")[2])
            if jfield.split(".")[1] == "0":
                D = -D
            x = Ra.gen()
            if D % 4 == 1:
                K = NumberField(x**2 - x - (D - 1)//4, 'a')
            else:
                K = NumberField(x**2 - D//4, 'a')
            if K.class_number() == 1:
                jj = K((f).padded_list(K.degree()))
                jfac = latex(jj.factor())
                s = f"${jfac}$"
        if s is None:
            d = f.denominator()
            if d == 1:
                s = web_latex(f)
            else:
                s = fr"$\tfrac{{1}}{{{latex(d.factor())}}} \left({latex(d*f)}\right)$"
    else:
        if "/" in j:
            fac = f" = {latex(QQ(j).factor())}"
            a, b = j.split("/")
            s = r"$\tfrac{%s}{%s}%s$" % (a, b, fac)
        elif j != "0":
            s = f"${j} = {latex(ZZ(j).factor())}$"
        else:
            s = "$0$"
    if resfield == "1.1.1.1":
        url = url_for("ec.rational_elliptic_curves", jinv=j, showcol="jinv")
    else:
        if jorig is None:
            jorig = j
        # ECNF search wants j-invariants formatted as a polynomial
        if "," in j:
            j = str(f).replace(" ", "")
        url = url_for("ecnf.index", jinv=j, field=resfield, showcol="jinv")
    return '<a href="%s">%s</a>' % (url, s)

def canonicalize_name(name):
    cname = "X" + name[1:].lower().replace("_", "").replace("^", "")
    if cname[:4] == "Xs4(":
        cname = cname.upper()
    elif cname in ["X1(2,2)", "Xpm1(2,2)", "Xsp(2)"]:
        cname = "X(2)"
    elif cname in ["X1(2)", "Xpm1(2)", "Xsp+(2)"]:
        cname = "X0(2)"
    elif cname == "Xpm1(3)":
        cname = "X0(3)"
    elif cname == "Xns+(2)":
        cname = "X(1)"
    elif cname == "Xpm1(4)":
        cname = "X0(4)"
    elif cname == "Xpm1(6)":
        cname = "X0(6)"
    return cname

def name_to_latex(name):
    if not name:
        return ""
    name = canonicalize_name(name)
    if "+" in name:
        name = name.replace("+", "^+")
    if "ns" in name:
        name = name.replace("ns", r"{\mathrm{ns}}")
    elif "sp" in name:
        name = name.replace("sp", r"{\mathrm{sp}}")
    elif "S4" in name:
        name = name.replace("S4", "{S_4}")
    elif "pm1" in name:
        name = name.replace("pm1", r"{\pm1}")
    if name[1] != "(":
        name = "X_" + name[1:]
    return f"${name}$"

def factored_conductor(conductor):
    return "\\cdot".join(f"{p}{showexp(e, wrap=False)}" for (p, e) in conductor) if conductor else "1"

def remove_leading_coeff(jfac):
    if "(%s)" % jfac.unit() == (str(jfac).split("*")[0]).replace(' ',''):
        return "*".join(str(jfac).split("*")[1:])
    else:
        return str(jfac)

def formatted_dims(dims, mults):
    if not dims:
        return ""
    # Collapse newforms with the same dimension
    collapsed = Counter()
    for d, c in zip(dims, mults):
        collapsed[d] += c
    dims, mults = zip(*(sorted(collapsed.items())))
    return "$" + r"\cdot".join(f"{d}{showexp(c, wrap=False)}" for (d, c) in zip(dims, mults)) + "$"

def formatted_newforms(newforms, mults):
    if not newforms:
        return ""
    return ", ".join(f'<a href="{url_for_mf_label(label)}">{label}</a>{showexp(c)}' for (label, c) in zip(newforms, mults))

def formatted_model(m):
    #lines = [teXify_pol(l).lower() for l in m["equation"].replace(" ","").split("=")]
    lines = ["0"] + [teXify_pol(l).lower() for l in m["equation"]]
    #if len(lines)>2: #display as 0 = ...
    #    lines = ["0"] + [l for l in lines if l != "0"]
    return (lines, m["number_variables"], m["model_type"],  m["smooth"])

def formatted_map(m, codomain_name="X(1)", codomain_equation=[]):
    f = {}
    for key in ["degree", "domain_model_type", "codomain_label", "codomain_model_type"]:
        f[key] = m[key]
    nb_coords = len(m["coordinates"])
    f["codomain_name"] = codomain_name
    varhigh = "XYZWTUVRSABCDEFGHIKLMNOPQJ"
    ce = f["codomain_equation"] = ["0"] + [teXify_pol(l).upper() for l in codomain_equation]
    lead = m["leading_coefficients"]
    if lead is None:
        lead = ["1"]*nb_coords
    else:
        lead = [c.replace("*", r"\cdot") for c in lead]
    eqs = [teXify_pol(p).lower() for p in m["coordinates"]]
    if nb_coords == 2 and not (f["codomain_label"] == "1.1.0.a.1" and f["codomain_model_type"] == 4):
        nb_coords = 1
        f["coord_names"] = ["f"]
    elif nb_coords <= 26:
        f["coord_names"] = varhigh[:nb_coords]
    else: #x0,...,xn
        f["coord_names"] = ["x_{%s}" % i for i in range(nb_coords)]
    f["nb_coords"] = nb_coords

    if nb_coords == 1: #display only one coordinate as a quotient
        if lead[0][0] == "-":
            sgn = "-"
            lead[0] = lead[0][1:]
        else:
            sgn = ""
        if eqs[1] == "1" and lead == ["1","1"]:
            equations = [eqs[0]]
        elif eqs[1] == "1" and lead[1] == "1" and m["factored"] and eqs[0].count("(") > 0:
            equations = ["{}{}".format(lead[0], eqs[0])]
        elif eqs[1] == "1" and lead[1] == "1":
            equations = ["{}({})".format(lead[0], eqs[0])]
        elif eqs[1] == "1":
            equations = [r"\frac{%s}{%s}" % (eqs[0], lead[0])]
        elif lead == ["1","1"]:
            equations = [r"\frac{%s}{%s}" % (eqs[0], eqs[1])]
        elif lead[1] == "1":
            equations = [r"%s\,\frac{%s}{%s}" % (lead[0], eqs[0], eqs[1])]
        else:
            equations = [r"\frac{%s}{%s}\cdot\frac{%s}{%s}" % (lead[0], lead[1], eqs[0], eqs[1])]
        equations[0] = sgn + equations[0]
    else: #2 or more coordinates, do not display as quotients
        equations = []
        for j in range(len(eqs)):
            if lead[j] == "1":
                equations.append(eqs[j])
            elif m["factored"] and eqs[j].count("(") > 0:
                equations.append("{}{}".format(lead[j], eqs[j]))
            else:
                equations.append("{}({})".format(lead[j], eqs[j]))
    f["equations"] = equations
    return(f)

def difference(Ad, Bd, Am, Bm):
    # Ad and Bd are lists of dimensions, Am, Bm of multiplicities
    # Returns two lists (dims, mult) for A - B.
    if Ad is None:
        Ad, Am = [], []
    if Bd is None:
        Bd, Bm = [], []
    C = Counter()
    for d, m in zip(Ad, Am):
        C[d] += m
    for d, m in zip(Bd, Bm):
        C[d] -= m
    C = {d: m for (d,m) in C.items() if m != 0}
    if not C:
        return [], []
    return tuple(zip(*(sorted(C.items()))))

def modcurve_link(label):
    return '<a href="%s">%s</a>'%(url_for(".by_label",label=label),label)

def combined_data(label):
    data = db.gps_gl2zhat_fine.lookup(label)
    if data is None:
        return
    if not data["contains_negative_one"]:
        coarse = db.gps_gl2zhat_fine.lookup(data["coarse_label"], ["parents", "newforms", "obstructions", "traces"])
        data["coarse_parents"] = coarse.pop("parents")
        data.update(coarse)
    return data

class WebModCurve(WebObj):
    table = db.gps_gl2zhat_fine

    # We have to modify _get_dbdata, since we need to also include information from the coarse modular curve
    def _get_dbdata(self):
        return combined_data(self.label)

    @lazy_attribute
    def properties(self):
        props = [
            ("Label", self.label),
            ("Level", str(self.level)),
            ("Index", str(self.index)),
            ("Genus", str(self.genus)),
        ]
        if self.image is not None:
            props.append((None, self.image))
        if hasattr(self,"rank"):
            props.append(("Analytic rank", str(self.rank)))
        props.extend([("Cusps", str(self.cusps)),
                      (r"$\Q$-cusps", str(self.rational_cusps))])
        return props

    @lazy_attribute
    def image(self):
        img = db.modcurve_pictures.lookup(self.psl2label, "image")
        if img:
            return f'<img src="{img}" width="200" height="200"/>'

    @lazy_attribute
    def friends(self):
        friends = []
        if self.simple:
            friends.append(("Modular form " + self.newforms[0], url_for_mf_label(self.newforms[0])))
            if self.genus == 1:
                s = self.newforms[0].split(".")
                label = s[0] + "." + s[3]
                friends.append(("Isogeny class " + label, url_for("ec.by_ec_label", label=label)))
            if self.genus == 2:
                g2c_url = db.lfunc_instances.lucky({'Lhash':str(self.trace_hash), 'type' : 'G2Q'}, 'url')
                if g2c_url:
                    s = g2c_url.split("/")
                    label = s[2] + "." + s[3]
                    friends.append(("Isogeny class " + label, url_for("g2c.by_label", label=label)))
            friends.append(("L-function", "/L" + url_for_mf_label(self.newforms[0])))
        else:
            friends.append(("L-function not available",""))
        if self.genus > 0:
            for r in self.table.search({'trace_hash':self.trace_hash},['label','name','newforms']):
                if r['newforms'] == self.newforms and r['label'] != self.label:
                    friends.append(("Modular curve " + (r['name'] if r['name'] else r['label']),url_for("modcurve.by_label", label=r['label'])))
        return friends

    @lazy_attribute
    def bread(self):
        tail = []
        A = ["level", "index", "genus"]
        D = {}
        for a in A:
            D[a] = getattr(self, a)
            tail.append(
                (str(D[a]), url_for(".index_Q", **D))
            )
        tail.append((self.label, " "))
        return get_bread(tail)

    @lazy_attribute
    def display_name(self):
        if self.name:
            return name_to_latex(self.name)
        else:
            return self.label

    @lazy_attribute
    def title(self):
        return f"Modular curve {self.display_name}"

    @lazy_attribute
    def formatted_dims(self):
        return formatted_dims(self.dims, self.mults)

    @lazy_attribute
    def formatted_newforms(self):
        return formatted_newforms(self.newforms, self.mults)

    @lazy_attribute
    def obstruction_primes(self):
        if len(self.obstructions) < 10:
            return ",".join(str(p) for p in self.obstructions if p != 0)
        else:
            return ",".join(str(p) for p in self.obstructions[:3] if p != 0) + r",\ldots," + str(self.obstructions[-1])

    @lazy_attribute
    def coarse_description(self):
        if self.contains_negative_one:
            return r"yes"
        else:
            return r"no $\quad$ (see %s for the level structure with $-I$)"%(modcurve_link(self.coarse_label))

    @lazy_attribute
    def quadratic_refinements(self):
        if self.contains_negative_one:
            qtwists = list(self.table.search({'coarse_label':self.label}, 'label'))
            if len(qtwists) > 1:
                return r"%s"%(', '.join([modcurve_link(label) for label in qtwists if label != self.label]))
            else:
                return r"none in database"
        else:
            return "none"

    @lazy_attribute
    def cusps_display(self):
        if self.cusps == 1:
            return "$1$ (which is rational)"
        elif self.rational_cusps == 0:
            return f"${self.cusps}$ (none of which are rational)"
        elif self.rational_cusps == 1:
            return f"${self.cusps}$ (of which $1$ is rational)"
        elif self.cusps == self.rational_cusps:
            return f"${self.cusps}$ (all of which are rational)"
        else:
            return f"${self.cusps}$ (of which ${self.rational_cusps}$ are rational)"

    @lazy_attribute
    def cusp_widths_display(self):
        if not self.cusp_widths:
            return ""
        return "$" + r"\cdot".join(f"{w}{showexp(n, wrap=False)}" for (w,n) in self.cusp_widths) + "$"

    @lazy_attribute
    def cusp_orbits_display(self):
        if not self.cusp_orbits:
            return ""
        return "$" + r"\cdot".join(f"{w}{showexp(n, wrap=False)}" for (w,n) in self.cusp_orbits) + "$"

    @lazy_attribute
    def cm_discriminant_list(self):
        return ",".join(str(D) for D in self.cm_discriminants)

    @lazy_attribute
    def factored_conductor(self):
        return factored_conductor(self.conductor)

    @lazy_attribute
    def models_to_display(self):
        return list(db.modcurve_models_test.search({"modcurve": self.label, "dont_display": False}, ["equation", "number_variables", "model_type", "smooth"]))

    @lazy_attribute
    def formatted_models(self):
        return [formatted_model(m) for m in self.models_to_display]

    @lazy_attribute
    def models_count(self):
        return db.modcurve_models_test.count({"modcurve": self.label})

    @lazy_attribute
    def has_more_models(self):
        return len(self.models_to_display) < self.models_count

    @lazy_attribute
    def modelmaps_to_display(self):
        # Ensure domain model and map have dont_display = False
        domain_types = [1] + [m["model_type"] for m in self.models_to_display]
        return list(db.modcurve_modelmaps_test.search(
            {"domain_label": self.label,
             "dont_display": False,
             "domain_model_type":{"$in": domain_types}},
            ["degree", "domain_model_type", "codomain_label", "codomain_model_type",
             "coordinates", "leading_coefficients", "factored"]))

    def display_j(self, domain_model_type):
        jmaps = [m for m in self.modelmaps_to_display if m["codomain_label"] == "1.1.0.a.1" and m["domain_model_type"] == domain_model_type]
        return len(jmaps) >= 1

    def display_E4E6(self, domain_model_type):
        jmaps = [m for m in self.modelmaps_to_display if m["codomain_label"] == "1.1.0.a.1" and m["codomain_model_type"] == 4 and m["domain_model_type"] == domain_model_type]
        return len(jmaps) >= 1

    def model_type_str(self, model_type):
        if model_type == 0:
            return "canonical model"
        elif model_type in [2, -2]:
            return "plane model"
        elif model_type == 5:
            return "Weierstrass model"
        elif model_type == 7:
            # Should this be called something else?
            return "hyperelliptic model"
        elif model_type == 8:
            # Not sure what to call this either
            return "embedded model"
        return ""

    def model_type_knowl(self, model_type):
        if model_type == 0:
            return display_knowl('ag.canonical_model', 'Canonical model')
        elif model_type in [2, -2]:
            return display_knowl('modcurve.plane_model', 'Plane model')
        elif model_type == 5:
            if self.genus == 1:
                return display_knowl('ec.weierstrass_coeffs', 'Weierstrass model')
            else:
                return display_knowl('ag.hyperelliptic_curve', 'Weierstrass model')
        elif model_type == 8:
            return display_knowl('modcurve.embedded_model', 'Embedded model')
        return ""

    def model_type_domain(self, model_type):
        s = self.model_type_str(model_type)
        if s:
            s = f"from the {s} of this modular curve"
        return s

    def model_type_codomain(self, model_type):
        s = self.model_type_str(model_type)
        if s:
            s = f"the {s} of"
        return s

    def formatted_jmap(self, domain_model_type):
        jmaps = [m for m in self.modelmaps_to_display if m["codomain_label"] == "1.1.0.a.1" and m["domain_model_type"] == domain_model_type]
        jmap = [m for m in jmaps if m["codomain_model_type"] == 1]
        f1 = formatted_map(jmap[0]) if jmap else {}
        f = {}
        f["degree"] = jmaps[0]["degree"]
        f["domain_model_type"] = jmaps[0]["domain_model_type"]
        f["codomain_model_type"] = 1
        f["codomain_label"] = "1.1.0.a.1"
        f["codomain_name"] = "X(1)"
        f["codomain_equation"] = ""
        nb_coords = 0
        f["coord_names"] = []
        f["equations"] = []
        if jmap:
            nb_coords += 1
            f["equations"] += f1["equations"]
        if self.display_E4E6(domain_model_type):
            nb_coords += 1
            f["equations"] += [r"1728\,\frac{E_4^3}{E_4^3-E_6^2}"]
        f["nb_coords"] = nb_coords
        f["coord_names"] = ["j"] + [""]*(nb_coords-1)
        return(f)

    def formatted_E4E6(self, domain_model_type):
        E4E6 = [m for m in self.modelmaps_to_display if m["codomain_label"] == "1.1.0.a.1" and m["codomain_model_type"] == 4 and m["domain_model_type"] == domain_model_type][0]
        f = formatted_map(E4E6)
        f["coord_names"] = ["E_4", "E_6"]
        return(f)

    @lazy_attribute
    def formatted_modelisos(self):
        maps = [m for m in self.modelmaps_to_display if m["codomain_label"] == self.label]
        models = {rec["model_type"]: rec["equation"] for rec in self.models_to_display}
        maps = [formatted_map(m, codomain_name=self.name, codomain_equation=models[m["codomain_model_type"]]) for m in maps]
        return [(m["degree"], m["domain_model_type"], m["codomain_label"], m["codomain_model_type"], m["codomain_name"], m["codomain_equation"], m["coord_names"], m["equations"]) for m in maps]

    @lazy_attribute
    def formatted_jmaps(self):
        maps = []
        for domain_model_type in [0,8,1,-2]:
            if self.display_j(domain_model_type):
                maps.append(self.formatted_jmap(domain_model_type))
            if self.display_E4E6(domain_model_type):
                maps.append(self.formatted_E4E6(domain_model_type))
        return maps

    @lazy_attribute
    def other_formatted_maps(self):
        maps = [m for m in self.modelmaps_to_display if m["codomain_label"] not in [self.label, "1.1.0.a.1"]]
        res = []
        if maps:
            codomain_labels = [m["codomain_label"] for m in maps]
            codomains = list(db.gps_gl2zhat_fine.search(
                {"label": {"$in": codomain_labels}},
                ["label","name"]))
            # Do not display maps for which the codomain model has dont_display = False
            image_eqs = list(db.modcurve_models_test.search(
                {"modcurve": {"$in": codomain_labels},
                 "dont_display": False},
                ["modcurve", "model_type", "equation"]))
            for m in maps:
                codomain = [crv for crv in codomains if crv["label"] == m["codomain_label"]][0]
                codomain_name = codomain["name"]
                image_eq = [model for model in image_eqs
                            if model["modcurve"] == m["codomain_label"]
                            and model["model_type"] == m["codomain_model_type"]]
                if len(image_eq) > 0:
                    codomain_equation = image_eq[0]["equation"]
                    res.append(formatted_map(m, codomain_name=codomain_name,
                                             codomain_equation=codomain_equation))
        return res

    @lazy_attribute
    def all_formatted_maps(self):
        maps = self.formatted_jmaps + self.other_formatted_maps
        return [(m["degree"], m["domain_model_type"], m["codomain_label"], m["codomain_model_type"], m["codomain_name"], m["codomain_equation"], m["coord_names"], m["equations"]) for m in maps]

    @lazy_attribute
    def modelmaps_count(self):
        return db.modcurve_modelmaps_test.count({"domain_label": self.label})

    @lazy_attribute
    def has_more_modelmaps(self):
        return len(self.modelmaps_to_display) < self.modelmaps_count

    def cyclic_isogeny_field_degree(self):
        return min(r[1] for r in self.isogeny_orbits if r[0] == self.level)

    def cyclic_torsion_field_degree(self):
        return min(r[1] for r in self.orbits if r[0] == self.level)

    def full_torsion_field_degree(self):
        N = self.level
        P = integer_prime_divisors(N)
        GL2size = euler_phi(N) * N * (N // prod(P))**2 * prod(p**2 - 1 for p in P)
        return GL2size // self.index

    def show_generators(self):
        if not self.generators: # 2.6.0.a.1
            return "trivial subgroup"
        return ", ".join(r"$\begin{bmatrix}%s&%s\\%s&%s\end{bmatrix}$" % tuple(g) for g in self.generators)

    def show_subgroup(self):
        if self.Glabel:
            return abstract_group_display_knowl(self.Glabel)
        return ""

    def _curvedata(self, query, flip=False):
        # Return display data for covers/covered by/factorization
        curves = self.table.search(query, ["label", "coarse_label", "level", "index", "psl2index", "genus", "name", "rank", "newforms", "dims", "mults"])
        return [(
            C["label"],
            name_to_latex(C["name"]) if C.get("name") else C["label"],
            C["level"],
            C["index"] // self.index if flip else self.index // C["index"], # relative index
            C["psl2index"] // self.psl2index if flip else self.psl2index // C["psl2index"], # relative degree
            C["genus"],
            "" if C["rank"] is None else C["rank"],
            (formatted_dims(*difference(C["dims"], self.dims,
                                        C["mults"], self.mults)) if flip else
             formatted_dims(*difference(self.dims, C["dims"],
                                        self.mults, C["mults"]))))
                for C in curves]

    @lazy_attribute
    def modular_covers(self):
        return self._curvedata({"label":{"$in": self.parents}})

    @lazy_attribute
    def modular_covered_by(self):
        return self._curvedata({"parents":{"$contains": self.label}}, flip=True)

    @lazy_attribute
    def fiber_product_of(self):
        return self._curvedata({"label": {"$in": self.factorization, "$not": self.label}})

    @lazy_attribute
    def newform_level(self):
        if self.newforms is None:
            return 1
        return lcm([int(f.split('.')[0]) for f in self.newforms])

    @lazy_attribute
    def downloads(self):
        self.downloads = [
            (
                "Code to Magma",
                url_for(".modcurve_magma_download", label=self.label),
            ),
            (
                "Code to SageMath",
                url_for(".modcurve_sage_download", label=self.label),
            ),
            (
                "All data to text",
                url_for(".modcurve_text_download", label=self.label),
            ),
            (
                'Underlying data',
                url_for(".modcurve_data", label=self.label),
            )

        ]
        #self.downloads.append(("Underlying data", url_for(".belyi_data", label=self.label)))
        return self.downloads

    @lazy_attribute
    def known_degree1_points(self):
        return db.modcurve_points_test.count({"curve_label": self.label, "degree": 1, "cusp": False})

    @lazy_attribute
    def known_degree1_noncm_points(self):
        return db.modcurve_points_test.count({"curve_label": self.label, "degree": 1, "cm": 0, "cusp": False})

    @lazy_attribute
    def known_low_degree_points(self):
        return db.modcurve_points_test.count({"curve_label": self.label, "degree": {"$gt": 1}, "cusp": False})

    @lazy_attribute
    def db_points(self):
        return list(db.modcurve_points_test.search(
            {"curve_label": self.label},
            sort=["degree", "j_height"],
            projection=["Elabel","cm","isolated","jinv","j_field","j_height",
                        "jorig","residue_field","degree","coordinates"]))

    @lazy_attribute
    def rational_point_coord_types(self):
        pts = [pt["coordinates"] for pt in self.db_points if pt["degree"] == 1 and pt["coordinates"] is not None]
        return sorted(set(sum([[int(model_type) for model_type in pt] for pt in pts], [])))

    @lazy_attribute
    def rational_point_coord_headers(self):
        return "".join(f"<th>{self.model_type_knowl(t)}</th>" for t in self.rational_point_coord_types)

    @lazy_attribute
    def nf_point_coord_types(self):
        pts = [pt["coordinates"] for pt in self.db_points if pt["degree"] != 1 and pt["coordinates"] is not None]
        return sorted(set(sum([[int(model_type) for model_type in pt] for pt in pts], [])))

    @lazy_attribute
    def nf_point_coord_headers(self):
        return "".join(f"<th>{self.model_type_knowl(t)}</th>" for t in self.nf_point_coord_types)

    def get_coordstr(self, rec):
        if rec.get("coordinates") is None:
            return ""
        def make_point(coord):
            if rec["degree"] != 1:
                R = PolynomialRing(QQ, name="a")
                coord = [latex(R([QQ(t) for t in c.split(",")])) for c in coord.split(":")]
                coord = ":".join(coord)
            return f"$({coord})$"
        s = ""
        if rec["degree"] == 1:
            coord_types = self.rational_point_coord_types
        else:
            coord_types = self.nf_point_coord_types
        for model_type in coord_types:
            coords = rec["coordinates"][str(model_type)]
            coords = [make_point(coord) for coord in coords]
            s += f"<td>{', '.join(coords)}</td>"
        return s

    @lazy_attribute
    def db_rational_points(self):
        pts = []
        for rec in self.db_points:
            if rec["degree"] != 1: continue
            coordstr = self.get_coordstr(rec)
            pts.append(
                (rec["Elabel"],
                 url_for_EC_label(rec["Elabel"]) if rec["Elabel"] else "",
                 "no" if rec["cm"] == 0 else f'${rec["cm"]}$',
                 r"$\infty$" if not rec["jinv"] and not rec["j_height"] else showj(rec["jinv"]),
                 showj_fac(rec["jinv"]),
                 rec["j_height"],
                 coordstr))
        # Should sort pts
        return pts

    @lazy_attribute
    def db_nf_points(self):
        pts = []
        for rec in self.db_points:
            if rec["degree"] == 1: continue
            coordstr = self.get_coordstr(rec)
            pts.append(
                (rec["Elabel"],
                 url_for_ECNF_label(rec["Elabel"]) if rec["Elabel"] else "",
                 "no" if rec["cm"] == 0 else f'${rec["cm"]}$',
                 "yes" if rec["isolated"] == 4 else ("no" if rec["isolated"] in [2,-1,-2,-3,-4] else ""),
                 r"$\infty$" if not rec["jinv"] and not rec["j_height"] else showj_nf(rec["jinv"], rec["j_field"], rec["jorig"], rec["residue_field"]),
                 rec["residue_field"],
                 url_for_NF_label(rec["residue_field"]),
                 rec["j_field"],
                 url_for_NF_label(rec["j_field"]),
                 rec["degree"],
                 rec["j_height"],
                 coordstr))
        return pts

    @lazy_attribute
    def old_db_nf_points(self):
        # Use the db.ec_curvedata table to automatically find rational points
        #limit = None if (self.genus > 1 or self.genus == 1 and self.rank == 0) else 10
        if ZZ(self.level).is_prime():
            curves = list(db.ec_nfcurves.search(
                {"galois_images": {"$contains": self.Slabel},
                 "degree": {"$lte": self.genus}},
                one_per=["jinv"],
                projection=["label", "degree", "equation", "jinv", "cm"]))
            Ra = PolynomialRing(QQ,'a')
            return [(rec["label"],
                     url_for_ECNF_label(rec["label"]),
                     rec["equation"],
                     "no" if rec["cm"] == 0 else f'${rec["cm"]}$',
                     "yes" if (rec["degree"] < ZZ(self.q_gonality_bounds[0]) / 2 or rec["degree"] < self.q_gonality_bounds[0] and (self.rank == 0 or self.simple and rec["degree"] < self.genus)) else "",
                     web_latex(Ra([QQ(s) for s in rec["jinv"].split(',')]))) for rec in curves]
        else:
            return []

    @lazy_attribute
    def rational_points_description(self):
        curve = self
        if curve.known_degree1_noncm_points or curve.pointless is False:
            if curve.genus == 0 or (curve.genus == 1 and curve.rank > 0):
                if curve.level == 1:
                    return r'This modular curve has infinitely many rational points, corresponding to <a href="%s&all=1">elliptic curves over $\Q$</a>.' % url_for('ec.rational_elliptic_curves')
                elif curve.known_degree1_points > 0:
                    return 'This modular curve has infinitely many rational points, including <a href="%s">%s</a>.' % (
                        url_for('.low_degree_points', curve=curve.label, degree=1),
                        pluralize(curve.known_degree1_points, "stored non-cuspidal point"))
                else:
                    return r'This modular curve has infinitely many rational points but none with conductor small enough to be contained within the <a href="%s">database of elliptic curves over $\Q$</a>.' % url_for('ec.rational_elliptic_curves')
            elif curve.genus > 1 or (curve.genus == 1 and curve.rank == 0):
                if curve.rational_cusps and curve.cm_discriminants and curve.known_degree1_noncm_points > 0:
                    return 'This modular curve has rational points, including %s, %s and <a href="%s">%s</a>.' % (
                        pluralize(curve.rational_cusps, "rational cusp"),
                        pluralize(len(curve.cm_discriminants), "rational CM point"),
                        url_for('.low_degree_points', curve=curve.label, degree=1, cm='noCM'),
                        pluralize(curve.known_degree1_noncm_points, "known non-cuspidal non-CM point"))
                elif curve.rational_cusps and curve.cm_discriminants:
                    return 'This modular curve has %s and %s, but no other known rational points.' % (
                        pluralize(curve.rational_cusps, "rational cusp"),
                        pluralize(len(curve.cm_discriminants), "rational CM point"))
                elif curve.rational_cusps and curve.known_degree1_noncm_points > 0:
                    return 'This modular curve has rational points, including %s and <a href="%s">%s</a>.' % (
                        pluralize(curve.rational_cusps, "rational_cusp"),
                        url_for('.low_degree_points', curve=curve.label, degree=1, cm='noCM'),
                        pluralize(curve.known_degree1_noncm_points, "known non-cuspidal non-CM point"))
                elif curve.cm_discriminants and curve.known_degree1_noncm_points > 0:
                    return 'This modular curve has rational points, including %s and <a href="%s">%s</a>, but no rational cusps.' % (
                        pluralize(len(curve.cm_discriminants), "rational CM point"),
                        url_for('.low_degree_points', curve=curve.label, degree=1, cm='noCM'),
                        pluralize(curve.known_degree1_noncm_points, "known non-cuspidal non-CM point"))
                elif curve.rational_cusps:
                    return 'This modular curve has %s but no known non-cuspidal rational points.' % (
                        pluralize(curve.rational_cusps, "rational cusp"))
                elif curve.cm_discriminants:
                    return 'This modular curve has %s but no rational cusps or other known rational points.' % (
                        pluralize(len(curve.cm_discriminants), "rational CM point"))
                elif curve.known_degree1_points > 0:
                    return 'This modular curve has <a href="%s">%s</a> but no rational cusps or CM points.' % (
                        url_for('.low_degree_points', curve=curve.label, degree=1),
                        pluralize(curve.known_degree1_points, "known rational point"))
        else:
            if curve.obstructions == [0]:
                return 'This modular curve has no real points, and therefore no rational points.'
            elif 0 in curve.obstructions:
                return fr'This modular curve has no real points and no $\Q_p$ points for $p={curve.obstruction_primes}$, and therefore no rational points.'
            elif curve.obstructions:
                return fr'This modular curve has no $\Q_p$ points for $p={curve.obstruction_primes}$, and therefore no rational points.'
            elif curve.pointless is None:
                if curve.genus <= 90:
                    pexp = "$p$ not dividing the level"
                else:
                    pexp = "good $p < 8192$"
                return fr'This modular curve has real points and $\Q_p$ points for {pexp}, but no known rational points.'
            elif curve.genus > 1 or (curve.genus == 1 and curve.rank == 0):
                return "This modular curve has finitely many rational points, none of which are cusps."

    @lazy_attribute
    def nearby_lattice(self):
        def get_lig(label):
            return [ZZ(c) for c in label.split(".", 3)[:3]]
        # The poset of curves near this one in the lattice of subgroups of GL2(Zhat).
        # Goes up one level (higher index), and down to some collection of named curves
        # May be empty (if it's too far to a named curve)
        class LatNode:
            def __init__(self, label, x):
                self.label = label
                self.level, self.index, self.genus = get_lig(label)
                #if label == self.label:
                #    self.tex = self.label #r"\text{%s}" % self.label
                #else:
                if label in names:
                    self.tex = names[label]
                else:
                    level, index, genus = get_lig(label)
                    self.tex = "%s_{%s}^{%s}" % (self.level, self.index, self.genus)
                self.img = texlabels[self.tex]
                self.rank = sum(e for (p,e) in self.index.factor())
                self.x = x
        if "-" in self.label or not self.lattice_labels:
            return [],[]
        parents = {}
        names = {}
        for rec in db.gps_gl2zhat_fine.search({"label": {"$in": self.lattice_labels}}, ["label", "parents", "name"]):
            if rec["name"]:
                names[rec["label"]] = rec["name"]
            parents[rec["label"]] = rec["parents"]
        texlabels = []
        for label in self.lattice_labels:
            level, index, genus = get_lig(label)
            texlabels.append("%s_{%s}^{%s}" % (level, index, genus))
        texlabels = list(set(texlabels))
        texlabels.extend(names.values())
        texlabels = {rec["label"]: rec["image"] for rec in db.modcurve_teximages.search({"label": {"$in": list(texlabels)}})}
        nodes, edges = [], []
        for lab, x in zip(self.lattice_labels, self.lattice_x):
            nodes.append(LatNode(lab, x))
        nodes, edges = [LatNode(lab, x) for (lab, x) in zip(self.lattice_labels, self.lattice_x)], []
        if nodes:
            minrank = min(node.rank for node in nodes)
            for node in nodes: node.rank -= minrank
            # below = [node.label for node in nodes if node.index < self.index] -- why is this not used?
            above = [node.label for node in nodes if node.index > self.index]
            edges = [[lab, self.label] for lab in above] + [[self.label, lab] for lab in self.parents if lab in self.lattice_labels]
            for label, P in parents.items():
                edges.extend([[label, lab] for lab in P if lab in self.lattice_labels])
        return nodes, edges