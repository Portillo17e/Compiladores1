import json

from analizador import *


texto = """

int suma (int a, int b) {
    int c = a + b;
    if (c > 10) {
        return c;
    } else {
        return 0;
    }
}

"""
texto2 = """
void main() { 
while (x < 8) {
    x = x + 1;
    }
    int s = suma(3, 4);
    print(s);
    } 

"""

token = tokenize(texto)


# Analizador sintáctico
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def obtener_token_actual(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def coincidir(self, tipo_esperado):
        token_actual = self.obtener_token_actual()
        if token_actual and token_actual[0] == tipo_esperado:
            self.pos += 1
            return token_actual
        else:
            raise SyntaxError(f'Error sintáctico: se esperaba {tipo_esperado}, pero se encontró: {token_actual}')

    def parsear(self):
        # Punto de entrada del analizador: se espera una función
        return self.programa()
    
    def programa(self):
        funciones = []
        hay_main = False
        while self.obtener_token_actual():
            funcion = self.funcion()
            if funcion.nombre[1] == 'main':
                hay_main = True
            funciones.append(funcion)
        # if not hay_main:
        #     raise SyntaxError('Error sintáctico: se requiere una función main')
        return NodoPrograma(funciones) #

    # Función para reconocer declaraciones de variables dentro del cuerpo de la función y evaluar operaciones aritméticas más complejas:
    def funcion(self):
        # Gramática para una función: int IDENTIFICADOR (int IDENTIFICADOR*) {cuerpo}
        tipo_retorno = self.coincidir('KEYWORD')  # Tipo de retorno (ej. int)
        nombre_funcion = self.coincidir('IDENTIFIER')  # Nombre de la función
        print(nombre_funcion)
        if nombre_funcion[1] == 'main':
            self.coincidir('DELIMITER') # Se espera un "("
            self.coincidir('DELIMITER') # Se espera un ")"
            self.coincidir('DELIMITER') # Se espera un "{"
            parametros = []
        else:
            self.coincidir('DELIMITER')  # Se espera un "("
            parametros = self.parametros()
            self.coincidir('DELIMITER')  # Se espera un ")"
            self.coincidir('DELIMITER')  # Se espera un "{"
        cuerpo = self.cuerpo()
        self.coincidir('DELIMITER')  # Se espera un "}"
        return NodoFuncion(nombre_funcion, parametros, cuerpo)

    def parametros(self):
        parametros = []
        # Reglas para parámetros: int IDENTIFIER(, int IDENTIFIER)*
        tipo = self.coincidir('KEYWORD')  # Tipo del parámetro
        nombre = self.coincidir('IDENTIFIER')  # Nombre del parámetro
        parametros.append(NodoParametro(tipo, nombre))
        while self.obtener_token_actual() and self.obtener_token_actual()[1] == ',':
            self.coincidir('DELIMITER')  # Espera una ","
            tipo = self.coincidir('KEYWORD')  # Tipo del parámetro
            nombre = self.coincidir('IDENTIFIER')  # Nombre del parámetro
            parametros.append(NodoParametro(tipo, nombre))
        return parametros

    # Función para reconocer declaraciones de variables dentro del cuerpo de la función y evaluar operaciones aritméticas más complejas:


    def cuerpo(self):
        instrucciones = []
        while self.obtener_token_actual() and self.obtener_token_actual()[1] != "}":
            if self.obtener_token_actual()[1] == "return":
                instrucciones.append(self.retorno())
            elif self.obtener_token_actual()[1] == 'while':
                instrucciones.append(self.sentencia_while())
            elif self.obtener_token_actual()[1] == 'for':
                instrucciones.append(self.sentencia_for())
            elif self.obtener_token_actual()[1] == 'if':
                instrucciones.append(self.sentencia_if())
            elif self.obtener_token_actual()[1] == 'print':
                instrucciones.append(self.sentencia_print())
            else:
                instrucciones.append(self.asignacion())
        return instrucciones

    def retorno(self):
        self.coincidir('KEYWORD') # return
        expresion = self.expresion()
        self.coincidir('DELIMITER') # Final del statement ";"
        return NodoRetorno(expresion)


    def asignacion(self):
        if self.obtener_token_actual()[0] == "KEYWORD":
            tipo = self.coincidir("KEYWORD")
        nombre = self.coincidir("IDENTIFIER")
        self.coincidir("OPERATOR")
        expresion = self.expresion()
        self.coincidir("DELIMITER")
        return NodoAsignacion(nombre, expresion)

    def expresion(self):
        izquierda = self.termino()
        while self.obtener_token_actual() and self.obtener_token_actual()[0] == "OPERATOR":
            operador = self.coincidir("OPERATOR")
            derecha = self.termino()
            izquierda = NodoOperacion(izquierda, operador, derecha)
        return izquierda

    def termino(self):
        token = self.obtener_token_actual()
        if token[0] == "IDENTIFIER":
            return NodoIdentificador(self.coincidir("IDENTIFIER"))
        elif token[0] == "NUMBER":
            return NodoNumero(int(self.coincidir("NUMBER")[1]))
        else:
            raise SyntaxError(f"Error de sintaxis: se esperaba un identificador o un número, pero se encontró {token}")

    def sentencia_if(self):
        self.coincidir('KEYWORD')  # if
        self.coincidir('DELIMITER')  # (
        condicion = self.expresion()  # Condición ej x < 8
        self.coincidir('DELIMITER')  # )
        self.coincidir('DELIMITER')  # {
        cuerpo = self.cuerpo()
        self.coincidir('DELIMITER')  # Se espera un "}"
        if self.obtener_token_actual() and self.obtener_token_actual()[1] == 'else':
            self.coincidir('KEYWORD')  # else
            self.coincidir('DELIMITER') # {
            sino = self.cuerpo()
            self.coincidir('DELIMITER') # }
            return NodoIf(condicion, cuerpo, sino)
        return NodoIf(condicion, cuerpo)

    def sentencia_while(self):
        self.coincidir('KEYWORD')  # while
        self.coincidir('DELIMITER')  # (
        condicion = self.expresion()  # Condición ej x < 8
        self.coincidir('DELIMITER')  # )
        self.coincidir('DELIMITER')  # {
        cuerpo = self.cuerpo()
        self.coincidir('DELIMITER')  # Se espera un "}"

        return NodoWhile(condicion, cuerpo)
    
    def contenido(self):
        token = self.obtener_token_actual()
        if token[0] == "OPERATOR":
            return self.coincidir("OPERATOR")[1]
        elif token[0] == "IDENTIFIER":
            return self.coincidir("IDENTIFIER")[1]
        elif token[0] == "NUMBER":
            return self.coincidir("NUMBER")[1]
        else:
            return ""

    # print("a es igual a 8");
    def sentencia_print(self):
        self.coincidir('KEYWORD')  # print
        self.coincidir('DELIMITER')  # (
        texto = []
        self.coincidir('OPERATOR')  # "
        while self.obtener_token_actual() and self.obtener_token_actual()[1] != '"':
            texto.append(self.contenido())
        elementos = " ".join(texto)
        self.coincidir('OPERATOR')  # "
        self.coincidir('DELIMITER')  # )
        self.coincidir('DELIMITER')  # ;
        return NodoPrint(elementos)

    def sentencia_for(self):
        self.coincidir('KEYWORD')  # for
        self.coincidir('DELIMITER')  # (
        # Inicialización (ej: int i = 0)
        self.coincidir('KEYWORD')  # int
        identificador = self.coincidir('IDENTIFIER')  # Nombre de la variable
        self.coincidir('OPERATOR')  # Asignación (=)
        inicializacion = self.termino()  # Número o identificador
        self.coincidir('DELIMITER')  # ;
        # Condición (ej: i < 8)
        condicion = self.expresion()
        self.coincidir('DELIMITER')  # ;
        # Actualización (ej: i = i + 1)
        variable_actualizacion = self.coincidir('IDENTIFIER')  # Variable de control
        self.coincidir('OPERATOR')  # Operador de asignación (=)
        actualizacion = self.expresion()
        self.coincidir('DELIMITER')  # )
        self.coincidir('DELIMITER')  # {
        cuerpo = self.cuerpo()
        self.coincidir('DELIMITER')  # }

        return NodoFor((identificador, inicializacion), condicion, (variable_actualizacion, actualizacion), cuerpo)

def imprimir_ast(nodo):
    if isinstance(nodo, NodoPrograma):
        return {'Programa': [imprimir_ast(f) for f in nodo.funciones]}
    elif isinstance(nodo, NodoFuncion):
        return {'Funcion': nodo.nombre,
                'Parametros': [imprimir_ast(p) for p in nodo.parametros],
                'Cuerpo': [imprimir_ast(c) for c in nodo.cuerpo]}
    elif isinstance(nodo, NodoParametro):
        return {'Parametro': nodo.nombre, 'Tipo': nodo.tipo}
    elif isinstance(nodo, NodoWhile):
        return {'While': [imprimir_ast(nodo.condicion), [imprimir_ast(c) for c in nodo.cuerpo]]}
    elif isinstance(nodo, NodoIf):
        return {'If': [imprimir_ast(nodo.condicion), [imprimir_ast(c) for c in nodo.cuerpo]], 'Else': [imprimir_ast(c) for c in nodo.sino]}
    elif isinstance(nodo, NodoAsignacion):
        return {'Asignacion': nodo.nombre,
                'Expresion': imprimir_ast(nodo.expresion)}
    elif isinstance(nodo, NodoPrint):
        return {'Print': nodo.expresion}
    elif isinstance(nodo, NodoTexto):
        return {'Texto': nodo.valor}
    elif isinstance(nodo, NodoFor):
        return {'For': {
                    'Inicializacion': f"{nodo.inicializacion[0]} {imprimir_ast(nodo.inicializacion[1])}",
                    'Condicion': imprimir_ast(nodo.condicion),
                    'Actualizacion': f"{nodo.actualizacion[0]} {imprimir_ast(nodo.actualizacion[1])}",
                    'Cuerpo': [imprimir_ast(c) for c in nodo.cuerpo]
                }}
    elif isinstance(nodo, NodoOperacion):
        return {'Operacion': nodo.operador,
                'Izquierda': imprimir_ast(nodo.izquierda),
                'Derecha': imprimir_ast(nodo.derecha)}
    elif isinstance(nodo, NodoRetorno):
        return {'Return': imprimir_ast(nodo.expresion)}
    elif isinstance(nodo, NodoIdentificador):
        return {'Identificador': nodo.nombre}
    elif isinstance(nodo, NodoNumero):
        return {'Numero': nodo.valor}

    return {}

#  Aquí se prueba
try:
    print('Se inicia el análisis sintáctico')
    parser = Parser(token)
    arbol_ast = parser.parsear()
    codigo_asm = arbol_ast.generar_codigo()
    print(codigo_asm)
    
    # nodo_exp = NodoOperacion(NodoNumero(2), '+', NodoNumero(0))
    # print(json.dumps(imprimir_ast(nodo_exp), indent=1))
    # exp_op = nodo_exp.optimizar()
    # print(json.dumps(imprimir_ast(exp_op), indent=1))
    
    # print('Análisis sintáctico exitoso')
    # print(json.dumps(imprimir_ast(arbol_ast), indent=1))

except SyntaxError as e:
    print(e)

