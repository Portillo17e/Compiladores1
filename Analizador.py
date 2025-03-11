import re
import json
texto = """
int suma(int a , int b){
    int c = a + b;
    return c;
}

void main(){
    suma(4,5);
}
"""

# Definir patrones de tokens
token_patron = {
    "KEYWORD": r'\b(if|else|return|int|float|void|class|while|for|printf)\b',
    "IDENTIFIER": r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',
    "NUMBER": r'\b\d+\b',
    "OPERATOR": r'[\+\-\*/=<>!]',  # Operadores básicos
    "DELIMITER": r'[(),;{}]',  # Paréntesis, llaves, punto y coma
    "STRING": r'"[^"]*"',  # Cadenas de texto entre comillas
    "WHITESPACE": r'\s+'  # Espacios en blanco
}

def tokenize(text):
    patron_general = "|".join(f"(?P<{token}>{patron})" for token, patron in token_patron.items())
    patron_regex = re.compile(patron_general)

    tokens_encontrados = []
    for match in patron_regex.finditer(text):
        for token, valor in match.groupdict().items():
            if valor is not None and token != "WHITESPACE":
                tokens_encontrados.append((token, valor))

    return tokens_encontrados

tokens = tokenize(texto)

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
        while self.obtener_token_actual():
            self.funcion()
        print('Análisis sintáctico exitoso')

    def funcion(self):
        self.coincidir('KEYWORD')  # int o void
        nombre_funcion = self.coincidir('IDENTIFIER')  # Nombre de la función

        self.coincidir('DELIMITER')  # (
        if nombre_funcion[1] != 'main':
            self.parametros()
        self.coincidir('DELIMITER')  # )
        self.coincidir('DELIMITER')  # {
        self.cuerpo(nombre_funcion[1])  # Pasamos el nombre de la función aquí
        self.coincidir('DELIMITER')  # }


    def parametros(self):
        if self.obtener_token_actual() and self.obtener_token_actual()[0] == 'KEYWORD':
            self.coincidir('KEYWORD')  # int
            self.coincidir('IDENTIFIER')  # nombre del parámetro
            while self.obtener_token_actual() and self.obtener_token_actual()[1] == ',':
                self.coincidir('DELIMITER')  # ,
                self.coincidir('KEYWORD')  # int
                self.coincidir('IDENTIFIER')  # nombre del parámetro

    def cuerpo(self, nombre_funcion):
        while self.obtener_token_actual() and self.obtener_token_actual()[1] != '}':
            token_actual = self.obtener_token_actual()
            if token_actual[0] == 'KEYWORD' and token_actual[1] == 'return':
                self.coincidir('KEYWORD')
                self.expresion()
                self.coincidir('DELIMITER')  # ;
            elif token_actual[0] == 'KEYWORD':  # Declaración de variable
                self.declaracion_variable()
            elif token_actual[0] == 'IDENTIFIER':
                if self.obtener_token_actual()[1] == 'printf':
                    self.funcion_printf()
                elif nombre_funcion == 'main':  # Permitir llamadas a funciones en main
                    self.llamada_funcion()
                else:
                    self.asignacion()
            else:
                raise SyntaxError(f'Error sintáctico inesperado en {token_actual}')

    def declaracion_variable(self):
        self.coincidir('KEYWORD')  # int, float, etc.
        self.coincidir('IDENTIFIER')  # nombre de la variable
        if self.obtener_token_actual() and self.obtener_token_actual()[0] == 'OPERATOR' and self.obtener_token_actual()[1] == '=':
            self.coincidir('OPERATOR')  # =
            self.expresion()  # Valor asignado
        self.coincidir('DELIMITER')  # ;


    def funcion_printf(self):
        self.coincidir('IDENTIFIER')  # printf o print
        self.coincidir('DELIMITER')  # (
        self.expresion()  # Permitir imprimir variables y números
        self.coincidir('DELIMITER')  # )
        self.coincidir('DELIMITER')  # ;

    def asignacion_o_llamada(self):
        self.coincidir('IDENTIFIER')  # Nombre de la variable o función
        if self.obtener_token_actual() and self.obtener_token_actual()[1] == '=':
            self.coincidir('OPERATOR')  # =
            if self.obtener_token_actual()[0] == 'IDENTIFIER':  # Puede ser una función
                self.llamada_funcion()
            else:
                self.expresion()
        elif self.obtener_token_actual() and self.obtener_token_actual()[1] == '(':
            self.llamada_funcion()
        self.coincidir('DELIMITER')  # ;

    def llamada_funcion(self):
        self.coincidir('IDENTIFIER')  # Nombre de la función
        self.coincidir('DELIMITER')  # (
        if self.obtener_token_actual() and self.obtener_token_actual()[0] in ['IDENTIFIER', 'NUMBER']:
            self.expresion()
            while self.obtener_token_actual() and self.obtener_token_actual()[1] == ',':
                self.coincidir('DELIMITER')  # ,
                self.expresion()
        self.coincidir('DELIMITER')  # )
        if self.obtener_token_actual() and self.obtener_token_actual()[1] == ';':
            self.coincidir('DELIMITER')  # ;

        
    def expresion(self):
        if self.obtener_token_actual()[0] in ['IDENTIFIER', 'NUMBER']:
            self.coincidir(self.obtener_token_actual()[0])  # variable o número
            while self.obtener_token_actual() and self.obtener_token_actual()[0] == 'OPERATOR':
                self.coincidir('OPERATOR')  # +, -, *, /
                if self.obtener_token_actual()[0] in ['IDENTIFIER', 'NUMBER']:
                    self.coincidir(self.obtener_token_actual()[0])  # otra variable o número
                else:
                    raise SyntaxError(f'Error sintáctico: se esperaba IDENTIFIER o NUMBER, pero se encontró: {self.obtener_token_actual()}')



# Definición de nodos AST
class NodoAST:
    def __init__(self, tipo, valor=None):
        self.tipo = tipo
        self.valor = valor
        self.hijos = []
    def to_dict(self):
        def convertir_a_dict(valor):
            if isinstance(valor, NodoAST):
                return valor.to_dict()
            elif isinstance(valor, list):
                return [convertir_a_dict(v) for v in valor]
            else:
                return valor
        return {key: convertir_a_dict(value) for key, value in self.__dict__.items()}
    
    def agregar_hijo(self, nodo):
        self.hijos.append(nodo)
    
    def a_json(self):
        return {
            "tipo": self.tipo,
            "valor": self.valor,
            "hijos": [hijo.a_json() for hijo in self.hijos]
        } 

class NodoFuncion(NodoAST):
    def __init__(self, nombre, parametros, cuerpo):
        self.tipo = "Funcion"
        self.nombre = nombre
        self.parametros = parametros
        self.cuerpo = cuerpo

class NodoParametro(NodoAST):
    def __init__(self, tipo, nombre):
        self.tipo = "Parametro"
        self.tipo_dato = tipo
        self.nombre = nombre

class NodoAsignacion(NodoAST):
    def __init__(self, tipo, nombre, expresion):
        self.tipo = "Asignacion"
        self.tipo_dato = tipo
        self.nombre = nombre
        self.expresion = expresion

class NodoOperacion(NodoAST):
    def __init__(self, izquierda, operador, derecha):
        self.tipo = "Operacion"
        self.izquierda = izquierda
        self.operador = operador
        self.derecha = derecha

class NodoRetorno(NodoAST):
    def __init__(self, expresion):
        self.tipo = "Retorno"
        self.expresion = expresion

class NodoIdentificador(NodoAST):
    def __init__(self, nombre):
        self.tipo = "Identificador"
        self.nombre = nombre

class NodoNumero(NodoAST):
    def __init__(self, valor):
        self.tipo = "Numero"
        self.valor = int(valor) if valor.isdigit() else float(valor)

def imprimir_json(nodo):
    print(json.dumps(nodo.to_dict(), indent=4))

try:
    print('Se inicia el análisis sintáctico')
    parser = Parser(tokens)
    parser.parsear()
except SyntaxError as e:
    print(e)



def analizador_sintactico(texto):
    raiz = NodoAST("Programa")
    funcion_suma = NodoAST("Funcion", "suma")
    parametros = NodoAST("Parametros")
    parametros.agregar_hijo(NodoAST("Parametro", "int a"))
    parametros.agregar_hijo(NodoAST("Parametro", "int b"))
    funcion_suma.agregar_hijo(parametros)
    cuerpo = NodoAST("Cuerpo")
    cuerpo.agregar_hijo(NodoAST("Declaracion", "int c = a + b"))
    cuerpo.agregar_hijo(NodoAST("Return", "c"))
    funcion_suma.agregar_hijo(cuerpo)
    raiz.agregar_hijo(funcion_suma)
    
    funcion_main = NodoAST("Funcion", "main")
    cuerpo_main = NodoAST("Cuerpo")
    cuerpo_main.agregar_hijo(NodoAST("Llamada", "suma(4,5)"))
    funcion_main.agregar_hijo(cuerpo_main)
    raiz.agregar_hijo(funcion_main)
    
    return raiz

ast = analizador_sintactico(texto)
resultado = {
    "codigo_fuente": texto,
    "AST": ast.a_json()
}

print(json.dumps(resultado, indent=4))
