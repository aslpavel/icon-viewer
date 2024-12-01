export class Iter<T> {
    iter: Iterator<T>;

    constructor(iterable: Iterable<T>) {
        this.iter = iterable[Symbol.iterator]();
    }

    [Symbol.iterator](): Iterator<T> {
        return this.iter;
    }

    next(): IteratorResult<T> {
        return this.iter.next();
    }

    static range(start: number, stop?: number, step: number = 1): Iter<number> {
        function* rangeGen() {
            if (stop === undefined) {
                stop = start;
                start = 0;
            }
            for (let i = start; step > 0 ? i < stop : i > stop; i += step) {
                yield i;
            }
        }
        return new Iter(rangeGen());
    }

    enumerate(): Iter<[number, T]> {
        return this.applyGenFn(function* enumerateGen(iter) {
            let index = 0;
            for (let item of iter) {
                yield [index, item];
                index += 1;
            }
        });
    }

    map<O>(mapFn: (item: T) => O): Iter<O> {
        return this.applyGenFn(function* mapGen(iter) {
            for (let item of iter) {
                yield mapFn(item);
            }
        });
    }

    filter(predFn: (item: T) => boolean): Iter<T> {
        return this.applyGenFn(function* filterGen(iter) {
            for (let item of iter) {
                if (predFn(item)) {
                    yield item;
                }
            }
        });
    }

    filterMap<O>(filterMapFn: (item: T) => O): Iter<NonNullable<O>> {
        return this.applyGenFn(function* filterMapGen(iter) {
            for (let outerItem of iter) {
                const innerItem = filterMapFn(outerItem);
                if (innerItem) {
                    yield innerItem;
                }
            }
        });
    }

    flatMap<O>(flatMapFn: (item: T) => Iterable<O>): Iter<O> {
        return this.applyGenFn(function* flatMapGen(iter) {
            for (let outerItem of iter) {
                let innerItems = flatMapFn(outerItem);
                if (innerItems) {
                    for (let innerItem of innerItems) {
                        yield innerItem;
                    }
                }
            }
        });
    }

    forEach(forEachFn: (item: T) => void): void {
        for (let item of this) {
            forEachFn(item);
        }
    }

    fold<O>(initialValue: O, foldFn: (acc: O, item: T) => O): O {
        let acc = initialValue;
        for (let item of this) {
            acc = foldFn(acc, item);
        }
        return acc;
    }

    collectArray(): Array<T> {
        return Array.from(this);
    }

    collectMap<K, V>(this: Iter<readonly [K, V]>): Map<K, V> {
        return new Map(this);
    }

    collectObject<V>(this: Iter<readonly [PropertyKey, V]>): {
        [k: string]: V;
    } {
        return Object.fromEntries(this);
    }

    private applyGenFn<O>(genFn: (iter: Iterable<T>) => Iterable<O>): Iter<O> {
        return new Iter(genFn(this));
    }
}
